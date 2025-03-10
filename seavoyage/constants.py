from enum import Enum

class UnitEnum(Enum):
    KM = "km"
    M = "m"
    MI = "mi"
    FT = "ft"
    IN = "in"
    DEG = "deg"
    CEN = "cen"
    RAD = "rad"
    NAUT = "naut"
    NM = "nm"
    YD = "yd"
    
    @staticmethod
    def values_list():
        return [unit.value for unit in UnitEnum]
    
class AvoidPassageEnum(Enum):
    BABALMANDAB = "babalmandab"
    BOSPORUS = "bosporus"
    GIBRALTAR = "gibraltar"
    SUEZ = "suez"
    PANAMA = "panama"
    ORMUZ = "ormuz"
    NORTHWEST = "northwest"
    MALACCA = "malacca"
    SUNDA = "sunda"
    CHILI = "chili"
    SOUTH_AFRICA = "south_africa"
    
    @staticmethod
    def values_list():
        return [passage.value for passage in AvoidPassageEnum]
    
    
if __name__ == "__main__":
    print(UnitEnum.values_list())
    print(AvoidPassageEnum.values_list())