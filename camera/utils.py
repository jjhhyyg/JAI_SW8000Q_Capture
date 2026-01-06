"""
eBUS SDK 工具函数
"""

import eBUS as eb
from typing import Optional, Tuple, Any, List
from dataclasses import dataclass


@dataclass
class ParameterInfo:
    """GenICam 参数信息"""
    name: str
    value: Any
    min_val: Optional[Any] = None
    max_val: Optional[Any] = None
    param_type: str = "unknown"
    is_readable: bool = True
    is_writable: bool = True


def get_pixel_format_string(pixel_type: int) -> str:
    """将像素类型转换为可读字符串"""
    pixel_formats = {
        eb.PvPixelMono8: "Mono8",
        eb.PvPixelRGB8: "RGB8",
        eb.PvPixelBGR8: "BGR8",
        eb.PvPixelRGBa8: "RGBa8",
        eb.PvPixelBGRa8: "BGRa8",
    }
    return pixel_formats.get(pixel_type, f"Unknown({pixel_type})")


def get_payload_type_string(payload_type: int) -> str:
    """将负载类型转换为可读字符串"""
    payload_types = {
        eb.PvPayloadTypeImage: "Image",
        eb.PvPayloadTypeChunkData: "ChunkData",
        eb.PvPayloadTypeRawData: "RawData",
        eb.PvPayloadTypeMultiPart: "MultiPart",
    }
    return payload_types.get(payload_type, f"Unknown({payload_type})")


def read_parameter(parameters, name: str) -> Tuple[bool, Any]:
    """
    读取 GenICam 参数值

    Args:
        parameters: PvGenParameterArray 对象
        name: 参数名称

    Returns:
        (success, value) 元组
    """
    param = parameters.Get(name)
    if param is None:
        return False, None

    result, is_readable = param.IsReadable()
    if not is_readable:
        return False, None

    result, gen_type = param.GetType()

    if gen_type == eb.PvGenTypeInteger:
        result, value = param.GetValue()
        return result.IsOK(), value
    elif gen_type == eb.PvGenTypeFloat:
        result, value = param.GetValue()
        return result.IsOK(), value
    elif gen_type == eb.PvGenTypeBoolean:
        result, value = param.GetValue()
        return result.IsOK(), value
    elif gen_type == eb.PvGenTypeString:
        result, value = param.GetValue()
        return result.IsOK(), value
    elif gen_type == eb.PvGenTypeEnum:
        result, value = param.GetValueString()
        return result.IsOK(), value

    return False, None


def write_parameter(parameters, name: str, value: Any) -> bool:
    """
    写入 GenICam 参数值

    Args:
        parameters: PvGenParameterArray 对象
        name: 参数名称
        value: 要写入的值

    Returns:
        是否成功
    """
    param = parameters.Get(name)
    if param is None:
        print(f"[write_parameter] 参数 '{name}' 不存在")
        return False

    result, is_available = param.IsAvailable()
    result, is_readable = param.IsReadable()
    result, is_writable = param.IsWritable()

    print(f"[write_parameter] 参数 '{name}': available={is_available}, readable={is_readable}, writable={is_writable}")

    if not is_writable:
        print(f"[write_parameter] 参数 '{name}' 不可写 - 可能需要先停止采集或解锁TLParamsLocked")
        return False

    result, gen_type = param.GetType()

    if gen_type == eb.PvGenTypeEnum:
        # 枚举类型使用字符串设置
        if isinstance(value, str):
            result = parameters.SetEnumValue(name, value)
        else:
            result = param.SetValue(value)
    else:
        result = param.SetValue(value)

    if not result.IsOK():
        print(f"[write_parameter] 设置参数 '{name}' = {value} 失败: {result.GetCodeString()} - {result.GetDescription()}")

    return result.IsOK()


def get_parameter_info(parameters, name: str) -> Optional[ParameterInfo]:
    """
    获取参数的详细信息

    Args:
        parameters: PvGenParameterArray 对象
        name: 参数名称

    Returns:
        ParameterInfo 对象或 None
    """
    param = parameters.Get(name)
    if param is None:
        return None

    result, is_readable = param.IsReadable()
    result, is_writable = param.IsWritable()
    result, gen_type = param.GetType()

    info = ParameterInfo(
        name=name,
        value=None,
        is_readable=is_readable,
        is_writable=is_writable
    )

    if gen_type == eb.PvGenTypeInteger:
        info.param_type = "integer"
        if is_readable:
            result, info.value = param.GetValue()
            result, info.min_val = param.GetMin()
            result, info.max_val = param.GetMax()
    elif gen_type == eb.PvGenTypeFloat:
        info.param_type = "float"
        if is_readable:
            result, info.value = param.GetValue()
            result, info.min_val = param.GetMin()
            result, info.max_val = param.GetMax()
    elif gen_type == eb.PvGenTypeBoolean:
        info.param_type = "boolean"
        if is_readable:
            result, info.value = param.GetValue()
    elif gen_type == eb.PvGenTypeString:
        info.param_type = "string"
        if is_readable:
            result, info.value = param.GetValue()
    elif gen_type == eb.PvGenTypeEnum:
        info.param_type = "enum"
        if is_readable:
            result, info.value = param.GetValueString()
    elif gen_type == eb.PvGenTypeCommand:
        info.param_type = "command"

    return info


def get_enum_entries(parameters, name: str) -> List[str]:
    """
    获取枚举参数的所有可选项

    Args:
        parameters: PvGenParameterArray 对象
        name: 枚举参数名称

    Returns:
        可选项字符串列表
    """
    entries = []
    enum_param = parameters.GetEnum(name)
    if enum_param is None:
        return entries

    result, count = enum_param.GetEntriesCount()
    if not result.IsOK():
        return entries

    for i in range(count):
        result, entry = enum_param.GetEntryByIndex(i)
        if entry:
            result, entry_name = entry.GetName()
            if result.IsOK():
                entries.append(entry_name)

    return entries


def execute_command(parameters, name: str) -> bool:
    """
    执行命令参数

    Args:
        parameters: PvGenParameterArray 对象
        name: 命令参数名称

    Returns:
        是否成功
    """
    param = parameters.Get(name)
    if param is None:
        return False

    result = param.Execute()
    return result.IsOK()
