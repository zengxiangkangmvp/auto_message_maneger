from .ExistMsgMaker import ExistMsgMaker
from .NotExistMsg import NotExistMsgMaker
from .FeedCardMaker import FeedCardMsgMaker

msgMakers = {
    "存在特定数据提示": ExistMsgMaker,
    "不存在特定数据提示": NotExistMsgMaker,
    "FeedCard": FeedCardMsgMaker,
}
