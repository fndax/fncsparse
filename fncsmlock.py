import asyncio

from irctokens import build, Line
from ircrobots import Bot as BaseBot
from ircrobots import Server as BaseServer
from ircrobots import ConnectionParams
from ircstates.numerics import *
from ircrobots.matching import Response, ANY, Nickname, Regex, ResponseOr, Formatless

with open("channels-in") as f:
    CHANLIST = f.read().splitlines()

CHANSERV = Nickname("ChanServ")

INFO_ENDOFINFO = Response("NOTICE", [ANY, Formatless("*** End of Info ***")], source=CHANSERV)
INFO_MLOCK     = Response("NOTICE", [ANY, Regex(r"Mode lock")], source=CHANSERV)
INFO_NOTREG    = Response("NOTICE", [ANY, Regex(r"is not registered\.")], source=CHANSERV)

class Server(BaseServer):
    async def line_read(self, line: Line):
        print(f"{self.name} < {line.format()}")
        if line.command == RPL_WELCOME:
            mlock = {}
            for channel in CHANLIST:
                await self.send(build("CHANSERV", ["INFO", channel]))

                while True:
                    line = await self.wait_for(ResponseOr(INFO_MLOCK, INFO_ENDOFINFO, INFO_NOTREG))
                    if line.params[1].startswith("Mode lock"):
                        _, _2, modes = line.params[1].partition(": ")
                        mlock[channel] = modes
                    else:
                        if not channel in mlock:
                            mlock[channel] = "unset"
                        break
            print(mlock)
            with open("channels-out", "w") as f:
                [f.write(f"{k}\t{v}\n") for k,v in mlock.items()]

    async def line_send(self, line: Line):
        print(f"{self.name} > {line.format()}")

class Bot(BaseBot):
    def create_server(self, name: str):
        return Server(self, name)

async def main():
    bot = Bot()
    params = ConnectionParams(nickname="testbot", host="chat.freenode.invalid", port=6697, tls=True, realname="Test Magical Robot (using jess's ircrobots <3)")
    await bot.add_server("freenode", params)

    await bot.run()

if __name__ == "__main__":
    asyncio.run(main())
