import asyncio

from irctokens import build, Line
from ircrobots import Bot as BaseBot
from ircrobots import Server as BaseServer
from ircrobots import ConnectionParams
from ircstates.numerics import *
from ircrobots.matching import Response, ANY, Nickname, Regex, ResponseOr, Formatless

import re
from typing import Dict

with open("channels-in") as f:
    CHANLIST = f.read().splitlines()

CHANSERV = Nickname("ChanServ")

INFO_ENDOFACCESS = Response("NOTICE", [ANY, Regex(r"End of .* FLAGS listing.")], source=CHANSERV)
INFO_ACLENTRY    = Response("NOTICE", [ANY, Regex(r"^[0-9]+\s+[^\s]+\s+")], source=CHANSERV)
INFO_NOTREG      = Response("NOTICE", [ANY, Regex(r"is not registered\.")], source=CHANSERV)
INFO_NOTAUTHED   = Response("NOTICE", [ANY, Regex(r"You are not authorized to perform this operation.")], source=CHANSERV)

class Server(BaseServer):
    async def line_read(self, line: Line):
        print(f"{self.name} < {line.format()}")
        if line.command == RPL_WELCOME:
            acls: Dict[str, str] = {}
            for channel in CHANLIST:
                await self.send(build("CHANSERV", ["ACCESS", channel, "LIST"]))

                while True:
                    line = await self.wait_for(ResponseOr(INFO_ACLENTRY, INFO_ENDOFACCESS, INFO_NOTREG, INFO_NOTAUTHED))
                    aclmatch = re.match(r"^[0-9]+\s+([^\s]+)\s+", line.params[1])
                    if aclmatch and aclmatch.group(1) == "freenode-staff":
                        continue
                    elif aclmatch and channel in acls:
                        acls[channel] += f", {aclmatch.group(1)}"
                    elif aclmatch:
                        acls[channel] = aclmatch.group(1)
                    else:
                        if not channel in acls:
                            acls[channel] = "N/A"
                        break
            print(acls)
            with open("channels-out-acls", "w") as f:
                [f.write(f"{k}\t{v}\n") for k,v in acls.items()]

    async def line_send(self, line: Line):
        print(f"{self.name} > {line.format()}")

class Bot(BaseBot):
    def create_server(self, name: str):
        return Server(self, name)

async def main():
    bot = Bot()
    params = ConnectionParams(nickname="daxbot", host="chat.freenode.net", port=6697, tls=True, realname="dax's Magical Robot (using jess's ircrobots <3)")
    await bot.add_server("freenode", params)

    await bot.run()

if __name__ == "__main__":
    asyncio.run(main())
