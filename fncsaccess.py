"""Creates an IRC bot, connects it to IRC, and then runs `CHANSERV ACCESS
CHANNELNAME LIST` on all channels in a file channels-in in the current
directory, then pulls a list of people on the ACL.

Needs a file channels-in in the current directory, which it ingests to provide
a list of channels.

Writes output to channels-out-acls in the current directory."""

from typing import Dict
import re
import asyncio

from irctokens import build, Line
from ircstates.numerics import RPL_WELCOME
from ircrobots import Bot as BaseBot
from ircrobots import Server as BaseServer
from ircrobots import ConnectionParams
from ircrobots.matching import Response, ANY, Nickname, Regex, ResponseOr

with open("channels-in") as channels_in:
    CHANLIST = channels_in.read().splitlines()

CHANSERV = Nickname("ChanServ")

INFO_ENDOFACCESS = Response("NOTICE", [ANY, Regex(r"End of .* FLAGS listing.")],
                            source=CHANSERV)
INFO_ACLENTRY = Response("NOTICE", [ANY, Regex(r"^[0-9]+\s+[^\s]+\s+")],
                         source=CHANSERV)
INFO_NOTREG = Response("NOTICE", [ANY, Regex(r"is not registered\.")],
                       source=CHANSERV)
INFO_NOTAUTHED = Response("NOTICE", [ANY, Regex(r"You are not authorized to" \
    "perform this operation.")], source=CHANSERV)

class Server(BaseServer):
    """Overridden Server class handling line reading and writing"""
    async def line_read(self, line: Line):
        print(f"{self.name} < {line.format()}")
        if line.command == RPL_WELCOME:
            acls: Dict[str, str] = {}
            for channel in CHANLIST:
                await self.send(build("CHANSERV", ["ACCESS", channel, "LIST"]))

                while True:
                    line = await self.wait_for(ResponseOr(INFO_ACLENTRY,
                                                          INFO_ENDOFACCESS,
                                                          INFO_NOTREG,
                                                          INFO_NOTAUTHED))

                    aclmatch = re.match(r"^[0-9]+\s+([^\s]+)\s+",
                                        line.params[1])

                    if aclmatch and aclmatch.group(1) == "freenode-staff":
                        continue

                    if aclmatch and channel in acls:
                        acls[channel] += f", {aclmatch.group(1)}"
                    elif aclmatch:
                        acls[channel] = aclmatch.group(1)
                    else:
                        if not channel in acls:
                            acls[channel] = "N/A"
                        break

            print(acls)
            with open("channels-out-acls", "w") as channels_out:
                for channel, acl in acls.items():
                    channels_out.write(f"{channel}\t{acl}\n")

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
