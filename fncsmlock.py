"""Creates an IRC bot, connects it to IRC, and then runs `CHANSERV INFO
CHANNELNAME` on all channels in a file channels-in in the current
directory, then pulls the MLOCK (if set) from that.

Needs a file channels-in in the current directory, which it ingests to provide
a list of channels.

Writes output to channels-out-mlock in the current directory."""

import asyncio

from irctokens import build, Line
from ircstates.numerics import RPL_WELCOME
from ircrobots import Bot as BaseBot
from ircrobots import Server as BaseServer
from ircrobots import ConnectionParams
from ircrobots.matching import ANY, Nick, Regex, Formatless
from ircrobots.matching import Response, ResponseOr

with open("channels-in") as f:
    CHANLIST = f.read().splitlines()

CHANSERV = Nick("ChanServ")

INFO_ENDOFINFO = Response("NOTICE", [ANY, Formatless("*** End of Info ***")],
                          source=CHANSERV)
INFO_MLOCK = Response("NOTICE", [ANY, Regex(r"Mode lock")], source=CHANSERV)
INFO_NOTREG = Response("NOTICE", [ANY, Regex(r"is not registered\.")],
                       source=CHANSERV)

class Server(BaseServer):
    """Overridden Server class handling line reading and writing"""
    async def line_read(self, line: Line):
        print(f"{self.name} < {line.format()}")
        if line.command == RPL_WELCOME:
            mlocks = {}
            for channel in CHANLIST:
                await self.send(build("CHANSERV", ["INFO", channel]))

                while True:
                    line = await self.wait_for(ResponseOr(INFO_MLOCK,
                                                          INFO_ENDOFINFO,
                                                          INFO_NOTREG))
                    if line.params[1].startswith("Mode lock"):
                        _, _2, modes = line.params[1].partition(": ")
                        mlocks[channel] = modes
                    else:
                        if not channel in mlocks:
                            mlocks[channel] = "unset"
                        break
            print(mlocks)
            with open("channels-out-mlock", "w") as channels_out:
                for channel, mlock in mlocks.items():
                    channels_out.write(f"{channel}\t{mlock}\n")

    async def line_send(self, line: Line):
        print(f"{self.name} > {line.format()}")

class Bot(BaseBot):
    """Basic Bot subclass"""
    def create_server(self, name: str):
        return Server(self, name)

async def main():
    """Add something that is almost but not quite freenode to the bot's
    connection parameters, then start it up."""
    bot = Bot()
    params = ConnectionParams(nickname="testbot", host="chat.freenode.invalid",
                              port=6697, tls=True, realname="Test Robot")
    await bot.add_server("freenode", params)

    await bot.run()

if __name__ == "__main__":
    asyncio.run(main())
