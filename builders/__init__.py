from .SimpleBuilder import SimpleBuilder
from .TwoDateDiffBuilder import TwoDateDiffBuilder
from .LinesBuilder import LinesBuilder
from .TablesBuilder import TablesBuilder
from .MultiLinesBuilder import MultiLinesBuilder

builder_dict = {
    "简单数据报表": SimpleBuilder,
    "多表格数据报表": TablesBuilder,
    "两日某列差距的报表": TwoDateDiffBuilder,
    "进度跟踪报表": LinesBuilder,
    "多条件汇总报表": MultiLinesBuilder,
}
