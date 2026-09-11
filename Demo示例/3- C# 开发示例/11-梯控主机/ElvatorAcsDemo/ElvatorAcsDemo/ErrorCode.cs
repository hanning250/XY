using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.ComponentModel;
using System.Reflection;

namespace ElvatorAcsDemo
{
    /// <summary>
    /// 错误码工具类
    /// </summary>
    public static class ErrorCodeUtils
    {
        /// <summary>
        /// 设备错误码枚举
        /// </summary>
        public enum ErrorCode
        {
            [Description("时间段重叠")]
            NET_ERR_TIME_OVERLAP = 1900,

            [Description("假日计划重叠")]
            NET_ERR_HOLIDAY_PLAN_OVERLAP = 1901,

            [Description("卡号未排序")]
            NET_ERR_CARDNO_NOT_SORT = 1902,

            [Description("卡号不存在")]
            NET_ERR_CARDNO_NOT_EXIST = 1903,

            [Description("卡号错误")]
            NET_ERR_ILLEGAL_CARDNO = 1904,

            [Description("防区处于布防状态(参数修改不允许)")]
            NET_ERR_ZONE_ALARM = 1905,

            [Description("不支持一人多卡")]
            NET_ERR_NOT_SUPPORT_ONE_MORE_CARD = 1920,

            [Description("删除的人脸不存在")]
            NET_ERR_DELETE_NO_EXISTENCE_FACE = 1921,

            [Description("离线采集中，无法响应")]
            NET_ERR_OFFLINE_CAPTURING = 1929,

            [Description("与门口机通信异常")]
            NET_DVR_ERR_OUTDOOR_COMMUNICATION = 1950,

            [Description("未设置房间号")]
            NET_DVR_ERR_ROOMNO_UNDEFINED = 1951,

            [Description("无呼叫")]
            NET_DVR_ERR_NO_CALLING = 1952,

            [Description("响铃")]
            NET_DVR_ERR_RINGING = 1953,

            [Description("正在通话")]
            NET_DVR_ERR_IS_CALLING_NOW = 1954,

            [Description("智能锁密码错误")]
            NET_DVR_ERR_LOCK_PASSWORD_WRONG = 1955,

            [Description("开关锁失败")]
            NET_DVR_ERR_CONTROL_LOCK_FAILURE = 1956,

            [Description("开关锁超时")]
            NET_DVR_ERR_CONTROL_LOCK_OVERTIME = 1957,

            [Description("智能锁设备繁忙")]
            NET_DVR_ERR_LOCK_DEVICE_BUSY = 1958,

            [Description("远程开锁功能未打开")]
            NET_DVR_ERR_UNOPEN_REMOTE_LOCK_FUNCTION = 1959
        }
    }

    /// <summary>
    /// 枚举扩展方法类
    /// </summary>
    public static class EnumHelper
    {
        /// <summary>
        /// 获取枚举值的Description属性值
        /// </summary>
        /// <param name="value">枚举值</param>
        /// <returns>Description属性值或枚举名称</returns>
        public static string GetDescription(this Enum value)
        {
            if (value == null)
                return string.Empty;

            Type type = value.GetType();
            string name = Enum.GetName(type, value);
            if (name == null)
                return string.Empty;

            FieldInfo field = type.GetField(name);
            if (field == null)
                return string.Empty;

            DescriptionAttribute attribute =
                Attribute.GetCustomAttribute(field, typeof(DescriptionAttribute)) as DescriptionAttribute;

            return attribute == null ? name : attribute.Description;
        }

        /// <summary>
        /// 根据错误码获取对应的描述信息
        /// </summary>
        /// <param name="errorCode">错误码</param>
        /// <returns>错误描述或"未知错误码"</returns>
        public static string GetErrorDescription(int errorCode)
        {
            if (Enum.IsDefined(typeof(ErrorCodeUtils.ErrorCode), errorCode))
            {
                return ((ErrorCodeUtils.ErrorCode)errorCode).GetDescription();
            }
            return "未知错误码";
        }
    }


    
}


