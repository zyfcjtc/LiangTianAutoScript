from tasks.ad import AdTask
from tasks.jianmuying import JianmuyingTask
from tasks.mobai import MobaiTask
from tasks.porridge import PorridgeTask

TASK_REGISTRY = {
    "粥棚": PorridgeTask,
    "膜拜": MobaiTask,
    "建木营": JianmuyingTask,
    "看广告": AdTask,
}
