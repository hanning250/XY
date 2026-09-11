using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Runtime.InteropServices;
using ElvatorAcsDemo.Common;
using System.Threading;
using System.IO;

namespace ElvatorAcsDemo
{
    class CardManage
    {
        public static ushort iPlanTemplateNumber;
        /// <summary>
        /// 卡下发
        /// </summary>
        /// <param name="lUserID">用户登录句柄</param>
        /// <param name="CardNo">卡号</param>
        /// <param name="iPlanTemplateNumber">关联门计划模板</param>
        public static void SetOneCard(int lUserID, string CardNo, ushort iPlanTemplateNumber)
        {
            var struCardCond = new CHCNetSDK.NET_DVR_CARD_COND();
            struCardCond.dwSize = (uint)Marshal.SizeOf(struCardCond);
            struCardCond.dwCardNum = 1;

            IntPtr ptrStruCond = Marshal.AllocHGlobal((int)struCardCond.dwSize);
            try
            {
                Marshal.StructureToPtr(struCardCond, ptrStruCond, false);
                int m_lSetCardCfgHandle = CHCNetSDK.NET_DVR_StartRemoteConfig(
                    lUserID,
                    CHCNetSDK.NET_DVR_SET_CARD,
                    ptrStruCond,
                    struCardCond.dwSize,
                    null,
                    IntPtr.Zero);
                if (m_lSetCardCfgHandle == -1)
                {
                    Console.WriteLine("建立下发卡长连接失败，错误码为" + CHCNetSDK.NET_DVR_GetLastError());
                    return;
                }
                else
                {
                    Console.WriteLine("建立下发卡长连接成功！");
                }
                var struCardRecord = new CHCNetSDK.NET_DVR_CARD_RECORD
                {
                    dwSize = (uint)Marshal.SizeOf(typeof(CHCNetSDK.NET_DVR_CARD_RECORD)),
                    byCardNo = new byte[CHCNetSDK.ACS_CARD_NO_LEN],
                    byCardType = 1,
                    byLeaderCard = 0,
                    byUserType = 0,
                    byDoorRight = new byte[32],
                    wCardRightPlan = new ushort[32],
                    byRes = new byte[64],
                };
                struCardRecord.Init();

                Array.Clear(struCardRecord.byCardNo, 0, CHCNetSDK.ACS_CARD_NO_LEN);
                byte[] cardNoBytes = Encoding.Default.GetBytes(CardNo);
                Array.Copy(cardNoBytes, struCardRecord.byCardNo, Math.Min(cardNoBytes.Length, CHCNetSDK.ACS_CARD_NO_LEN));

                struCardRecord.byCardType = 1;        // 普通卡
                struCardRecord.byLeaderCard = 0;      // 是否为首卡，0-否，1-是
                struCardRecord.byUserType = 0;        // 用户类型：0– 普通用户，1- 管理员用户

                struCardRecord.byDoorRight[0] = 1;    // 1层有权限
                struCardRecord.byDoorRight[1] = 1;    // 2层有权限

                struCardRecord.wCardRightPlan[0] = iPlanTemplateNumber;

                struCardRecord.struValid.byEnable = 1;
                struCardRecord.struValid.byBeginTimeFlag = 1;
                struCardRecord.struValid.byEnableTimeFlag = 1;

                // 开始时间：2023-01-01 00:00:00
                struCardRecord.struValid.struBeginTime.wYear = 2023;
                struCardRecord.struValid.struBeginTime.byMonth = 1;
                struCardRecord.struValid.struBeginTime.byDay = 1;
                struCardRecord.struValid.struBeginTime.byHour = 0;
                struCardRecord.struValid.struBeginTime.byMinute = 0;
                struCardRecord.struValid.struBeginTime.bySecond = 0;

                // 结束时间：2030-12-30 23:59:59
                struCardRecord.struValid.struEndTime.wYear = 2030;
                struCardRecord.struValid.struEndTime.byMonth = 12;
                struCardRecord.struValid.struEndTime.byDay = 30;
                struCardRecord.struValid.struEndTime.byHour = 23;
                struCardRecord.struValid.struEndTime.byMinute = 59;
                struCardRecord.struValid.struEndTime.bySecond = 59;

                IntPtr ptrStruCardRecord = Marshal.AllocHGlobal(Marshal.SizeOf(struCardRecord));
                try
                {

                    Marshal.StructureToPtr(struCardRecord, ptrStruCardRecord, false);
                    var struCardStatus = new CHCNetSDK.NET_DVR_CARD_STATUS();
                    struCardStatus.Init();
                    struCardStatus.dwSize = (uint)Marshal.SizeOf(struCardStatus);
                    IntPtr ptrStruCardStatus = Marshal.AllocHGlobal((int)struCardStatus.dwSize);
                    try
                    {
                        Marshal.StructureToPtr(struCardStatus, ptrStruCardStatus, false);
                        IntPtr pInt = Marshal.AllocHGlobal(sizeof(int));
                        try
                        {
                            Marshal.WriteInt32(pInt, 0);

                            while (true)
                            {
                                uint dwOutBuffSize = (uint)Marshal.SizeOf(typeof(CHCNetSDK.NET_DVR_CARD_STATUS));
                                uint dwOutDataLen = 0;
                                int dwState = CHCNetSDK.NET_DVR_SendWithRecvRemoteConfig(m_lSetCardCfgHandle, ptrStruCardRecord, struCardRecord.dwSize, ptrStruCardStatus, struCardRecord.dwSize, ref dwOutDataLen);
                                struCardStatus = (CHCNetSDK.NET_DVR_CARD_STATUS)Marshal.PtrToStructure(
                                    ptrStruCardStatus, typeof(CHCNetSDK.NET_DVR_CARD_STATUS));
                                switch (dwState)
                                {
                                    case -1:
                                        Console.WriteLine("NET_DVR_SendWithRecvRemoteConfig接口调用失败，错误码：" + CHCNetSDK.NET_DVR_GetLastError());
                                        goto exitLoop;

                                    case CHCNetSDK.NET_SDK_CONFIG_STATUS_NEED_WAIT:
                                        Console.WriteLine("配置等待");
                                        Thread.Sleep(10);
                                        continue;
                                    case CHCNetSDK.NET_SDK_CONFIG_STATUS_FAILED:
                                        string failedCardNo = Encoding.Default.GetString(struCardStatus.byCardNo).Trim();
                                        string failedDesc = EnumHelper.GetErrorDescription((int)struCardStatus.dwErrorCode);
                                        Console.WriteLine("下发卡失败, 卡号: " + failedCardNo + ", 错误信息:" + failedDesc);
                                        goto exitLoop;
                                    case CHCNetSDK.NET_SDK_CONFIG_STATUS_EXCEPTION:
                                        string exceptionCardNo = Encoding.Default.GetString(struCardStatus.byCardNo).Trim();
                                        string exceptionDesc = EnumHelper.GetErrorDescription((int)struCardStatus.dwErrorCode);
                                        Console.WriteLine("下发卡异常, 卡号: " + exceptionCardNo + ", 错误信息:" + exceptionDesc);
                                        goto exitLoop;
                                    case CHCNetSDK.NET_SDK_CONFIG_STATUS_SUCCESS:
                                        string cardNo = Encoding.Default.GetString(struCardStatus.byCardNo).Trim();
                                        if (struCardStatus.dwErrorCode != 0)
                                        {
                                            string errorDesc = EnumHelper.GetErrorDescription((int)struCardStatus.dwErrorCode);
                                            Console.WriteLine("下发卡成功,但是错误码信息： " + errorDesc + ", 卡号：" + cardNo);
                                        }
                                        else
                                        {
                                            Console.WriteLine("下发卡成功, 卡号: " + cardNo + ", 状态：" + struCardStatus.byStatus);
                                        }
                                        continue;
                                    case CHCNetSDK.NET_SDK_CONFIG_STATUS_FINISH:
                                        Console.WriteLine("下发卡完成");
                                        goto exitLoop;
                                    default:
                                        Console.WriteLine("未知状态码: " + dwState);
                                        goto exitLoop;
                                }
                            }
                        exitLoop: ;
                        }
                        finally
                        {
                            Marshal.FreeHGlobal(pInt);
                        }
                    }
                    finally
                    {
                        Marshal.FreeHGlobal(ptrStruCardStatus);
                    }
                }
                finally
                {
                    Marshal.FreeHGlobal(ptrStruCardRecord);
                }
                if (!CHCNetSDK.NET_DVR_StopRemoteConfig(m_lSetCardCfgHandle))
                {
                    Console.WriteLine("NET_DVR_StopRemoteConfig接口调用失败，错误码：" + CHCNetSDK.NET_DVR_GetLastError());
                }
                else
                {
                    Console.WriteLine("NET_DVR_StopRemoteConfig接口成功\n");
                }
            }
            finally
            {
                Marshal.FreeHGlobal(ptrStruCond);
            }
        }

        public static void GetOneCard(int lUserID, string cardNo)
        {
            var cardCond = new CHCNetSDK.NET_DVR_CARD_COND
            {
                dwSize = (uint)Marshal.SizeOf(typeof(CHCNetSDK.NET_DVR_CARD_COND)),
                dwCardNum = 1
            };
            IntPtr ptrCardCond = Marshal.AllocHGlobal(Marshal.SizeOf(cardCond));
            try
            {
                Marshal.StructureToPtr(cardCond, ptrCardCond, false);
                int configHandle = CHCNetSDK.NET_DVR_StartRemoteConfig(
                    lUserID,
                    CHCNetSDK.NET_DVR_GET_CARD,
                    ptrCardCond,
                    cardCond.dwSize,
                    null,
                    IntPtr.Zero);
                if (configHandle == -1)
                {
                    Console.WriteLine("建立查询卡参数长连接失败，错误码为：" + CHCNetSDK.NET_DVR_GetLastError());
                    return;
                }
                Console.WriteLine("建立查询卡参数长连接成功！");
                var cardSendData = new CHCNetSDK.NET_DVR_CARD_SEND_DATA
                {
                    dwSize = (uint)Marshal.SizeOf(typeof(CHCNetSDK.NET_DVR_CARD_SEND_DATA))
                };
                cardSendData.Init();
                Array.Clear(cardSendData.byCardNo, 0, CHCNetSDK.ACS_CARD_NO_LEN);
                byte[] cardNoBytes = Encoding.Default.GetBytes(cardNo);
                Array.Copy(cardNoBytes, cardSendData.byCardNo, Math.Min(cardNoBytes.Length, CHCNetSDK.ACS_CARD_NO_LEN));
                IntPtr ptrCardSendData = Marshal.AllocHGlobal(Marshal.SizeOf(cardSendData));
                try
                {
                    Marshal.StructureToPtr(cardSendData, ptrCardSendData, false);
                    var cardRecord = new CHCNetSDK.NET_DVR_CARD_RECORD
                    {
                        dwSize = (uint)Marshal.SizeOf(typeof(CHCNetSDK.NET_DVR_CARD_RECORD))
                    };
                    IntPtr ptrCardRecord = Marshal.AllocHGlobal(Marshal.SizeOf(cardRecord));
                    try
                    {
                        Marshal.StructureToPtr(cardRecord, ptrCardRecord, false);
                        uint outDataLen = 0;
                        while (true)
                        {
                            int state = CHCNetSDK.NET_DVR_SendWithRecvRemoteConfig(
                                configHandle,
                                ptrCardSendData,
                                cardSendData.dwSize,
                                ptrCardRecord,
                                (uint)Marshal.SizeOf(cardRecord),
                                ref outDataLen);
                            cardRecord = (CHCNetSDK.NET_DVR_CARD_RECORD)Marshal.PtrToStructure(
                                ptrCardRecord, typeof(CHCNetSDK.NET_DVR_CARD_RECORD));
                            switch (state)
                            {
                                case -1:
                                    Console.WriteLine("NET_DVR_SendWithRecvRemoteConfig查询卡参数调用失败，错误码：" + CHCNetSDK.NET_DVR_GetLastError());
                                    return;
                                case CHCNetSDK.NET_SDK_CONFIG_STATUS_NEED_WAIT:
                                    Console.WriteLine("配置等待");
                                    Thread.Sleep(10);
                                    continue;
                                case CHCNetSDK.NET_SDK_CONFIG_STATUS_FAILED:
                                    Console.WriteLine("获取卡参数失败, 卡号: " + cardNo);
                                    return;
                                case CHCNetSDK.NET_SDK_CONFIG_STATUS_EXCEPTION:
                                    Console.WriteLine("获取卡参数异常, 卡号: " + cardNo);
                                    return;
                                case CHCNetSDK.NET_SDK_CONFIG_STATUS_SUCCESS:
                                    try
                                    {
                                        string name = "";
                                        switch (AppTest.iCharEncodeType)
                                        {
                                            case 0:
                                            case 1:
                                            case 2:
                                                name = Encoding.GetEncoding("GBK").GetString(cardRecord.byName).Trim();
                                                break;
                                            case 6:
                                                name = Encoding.UTF8.GetString(cardRecord.byName).Trim();
                                                break;
                                            default:
                                                name = Encoding.Default.GetString(cardRecord.byName).Trim();
                                                break;
                                        }
                                        string retrievedCardNo = Encoding.Default.GetString(cardRecord.byCardNo).Trim();
                                        Console.WriteLine("获取卡参数成功, 卡号: " + retrievedCardNo + ", 卡类型：" + cardRecord.byCardType + ", 姓名：" + name + ", 卡计划模板：" + cardRecord.wCardRightPlan[0]);
                                        Console.WriteLine("是否限制起始时间的标志byBeginTimeFlag : " + cardRecord.struValid.byEnableTimeFlag);
                                        Console.WriteLine("是否限制终止时间的标志byEnableTimeFlag  : " + cardRecord.struValid.byBeginTimeFlag);
                                    }
                                    catch (Exception ex)
                                    {
                                        Console.WriteLine("解码卡信息异常: " + ex.Message);
                                    }
                                    continue;
                                case CHCNetSDK.NET_SDK_CONFIG_STATUS_FINISH:
                                    Console.WriteLine("获取卡参数完成");
                                    break;
                                default:
                                    Console.WriteLine("未知状态码: " + state);
                                    return;
                            }
                            break;
                        }
                    }
                    finally
                    {
                        Marshal.FreeHGlobal(ptrCardRecord);
                    }
                }
                finally
                {
                    Marshal.FreeHGlobal(ptrCardSendData);
                }
                if (!CHCNetSDK.NET_DVR_StopRemoteConfig(configHandle))
                {
                    Console.WriteLine("NET_DVR_StopRemoteConfig接口调用失败，错误码：" + CHCNetSDK.NET_DVR_GetLastError());
                }
                else
                {
                    Console.WriteLine("NET_DVR_StopRemoteConfig接口成功\n");
                }
            }
            finally
            {
                Marshal.FreeHGlobal(ptrCardCond);
            }
        }

        public static void GetAllCards(int lUserID)
        {
            var cardCond = new CHCNetSDK.NET_DVR_CARD_COND
            {
                dwSize = (uint)Marshal.SizeOf(typeof(CHCNetSDK.NET_DVR_CARD_COND)),
                dwCardNum = 0xFFFFFFFF,
                byRes = new byte[64]
            };
            IntPtr ptrCardCond = Marshal.AllocHGlobal(Marshal.SizeOf(cardCond));
            try
            {
                Marshal.StructureToPtr(cardCond, ptrCardCond, false);
                int configHandle = CHCNetSDK.NET_DVR_StartRemoteConfig(
                    lUserID,
                    CHCNetSDK.NET_DVR_GET_CARD,
                    ptrCardCond,
                    cardCond.dwSize,
                    null,
                    IntPtr.Zero);
                if (configHandle == -1)
                {
                    Console.WriteLine("建立查询卡长连接失败，错误码为" + CHCNetSDK.NET_DVR_GetLastError());
                    return;
                }
                Console.WriteLine("建立查询卡长连接成功！");
                var cardRecord = new CHCNetSDK.NET_DVR_CARD_RECORD
                {
                    dwSize = (uint)Marshal.SizeOf(typeof(CHCNetSDK.NET_DVR_CARD_RECORD))
                };
                IntPtr ptrCardRecord = Marshal.AllocHGlobal(Marshal.SizeOf(cardRecord));
                try
                {
                    Marshal.StructureToPtr(cardRecord, ptrCardRecord, false);
                    while (true)
                    {
                        int state = CHCNetSDK.NET_DVR_GetNextRemoteConfig(
                            configHandle,
                            ptrCardRecord,
                            (int)cardRecord.dwSize);
                        cardRecord = (CHCNetSDK.NET_DVR_CARD_RECORD)Marshal.PtrToStructure(
                            ptrCardRecord, typeof(CHCNetSDK.NET_DVR_CARD_RECORD));
                        switch (state)
                        {
                            case -1:
                                Console.WriteLine("NET_DVR_GetNextRemoteConfig接口调用失败，错误码：" + CHCNetSDK.NET_DVR_GetLastError());
                                return;
                            case CHCNetSDK.NET_SDK_CONFIG_STATUS_NEED_WAIT:
                                Console.WriteLine("配置等待");
                                Thread.Sleep(10);
                                continue;
                            case CHCNetSDK.NET_SDK_CONFIG_STATUS_FAILED:
                                Console.WriteLine("获取卡参数失败");
                                return;
                            case CHCNetSDK.NET_SDK_CONFIG_STATUS_EXCEPTION:
                                Console.WriteLine("获取卡参数异常");
                                return;
                            case CHCNetSDK.NET_SDK_CONFIG_STATUS_SUCCESS:
                                try
                                {
                                    // 解码姓名（根据字符编码类型）
                                    string name = "";
                                    switch (AppTest.iCharEncodeType)
                                    {
                                        case 0:
                                        case 1:
                                        case 2:
                                            name = Encoding.GetEncoding("GBK").GetString(cardRecord.byName).Trim();
                                            break;
                                        case 6:
                                            name = Encoding.UTF8.GetString(cardRecord.byName).Trim();
                                            break;
                                        default:
                                            name = Encoding.Default.GetString(cardRecord.byName).Trim();
                                            break;
                                    }
                                    string cardNo = Encoding.Default.GetString(cardRecord.byCardNo).Trim();
                                    Console.WriteLine("获取卡参数成功, 卡号: " + cardNo +
                                        ", 卡类型：" + cardRecord.byCardType +
                                        ", 姓名：" + name);
                                }
                                catch (Exception ex)
                                {
                                    Console.WriteLine("解码卡信息异常: " + ex.Message);
                                }
                                continue;
                            case CHCNetSDK.NET_SDK_CONFIG_STATUS_FINISH:
                                Console.WriteLine("获取卡参数完成");
                                break;
                            default:
                                Console.WriteLine("未知状态码: " + state);
                                return;
                        }
                        break;
                    }
                }
                finally
                {
                    Marshal.FreeHGlobal(ptrCardRecord);
                }
                if (!CHCNetSDK.NET_DVR_StopRemoteConfig(configHandle))
                {
                    Console.WriteLine("NET_DVR_StopRemoteConfig接口调用失败，错误码：" + CHCNetSDK.NET_DVR_GetLastError());
                }
                else
                {
                    Console.WriteLine("NET_DVR_StopRemoteConfig接口成功\n");
                }
            }
            finally
            {
                Marshal.FreeHGlobal(ptrCardCond);
            }
        }

        public static void DeleteOneCard(int lUserID, string cardNo)
        {
            var cardCond = new CHCNetSDK.NET_DVR_CARD_COND
            {
                dwSize = (uint)Marshal.SizeOf(typeof(CHCNetSDK.NET_DVR_CARD_COND)),
                dwCardNum = 1,
                byRes = new byte[64]
            };
            IntPtr ptrCardCond = Marshal.AllocHGlobal(Marshal.SizeOf(cardCond));
            try
            {
                Marshal.StructureToPtr(cardCond, ptrCardCond, false);
                int configHandle = CHCNetSDK.NET_DVR_StartRemoteConfig(
                    lUserID,
                    CHCNetSDK.NET_DVR_DEL_CARD,
                    ptrCardCond,
                    cardCond.dwSize,
                    null,
                    IntPtr.Zero);
                if (configHandle == -1)
                {
                    Console.WriteLine("建立删除卡长连接失败，错误码为" + CHCNetSDK.NET_DVR_GetLastError());
                    return;
                }
                Console.WriteLine("建立删除卡长连接成功！");
                var cardData = new CHCNetSDK.NET_DVR_CARD_SEND_DATA
                {
                    dwSize = (uint)Marshal.SizeOf(typeof(CHCNetSDK.NET_DVR_CARD_SEND_DATA))
                };
                cardData.Init();
                Array.Clear(cardData.byCardNo, 0, CHCNetSDK.ACS_CARD_NO_LEN);
                byte[] cardNoBytes = Encoding.Default.GetBytes(cardNo);
                Array.Copy(cardNoBytes, cardData.byCardNo, Math.Min(cardNoBytes.Length, CHCNetSDK.ACS_CARD_NO_LEN));
                var cardStatus = new CHCNetSDK.NET_DVR_CARD_STATUS
                {
                    dwSize = (uint)Marshal.SizeOf(typeof(CHCNetSDK.NET_DVR_CARD_STATUS))
                };
                while (true)
                {
                    IntPtr ptrInBuff = Marshal.AllocHGlobal(Marshal.SizeOf(cardData));
                    Marshal.StructureToPtr(cardData, ptrInBuff, false);
                    IntPtr ptrOutBuff = Marshal.AllocHGlobal(Marshal.SizeOf(cardStatus));
                    Marshal.StructureToPtr(cardStatus, ptrOutBuff, false);
                    uint outDataLen = 0;
                    int state = CHCNetSDK.NET_DVR_SendWithRecvRemoteConfig(
                    configHandle,
                    ptrInBuff,
                    cardData.dwSize,
                    ptrOutBuff,
                    cardStatus.dwSize,
                    ref outDataLen
                    );
                    switch (state)
                    {
                        case -1:
                            Console.WriteLine("NET_DVR_SendWithRecvRemoteConfig接口调用失败，错误码：" + CHCNetSDK.NET_DVR_GetLastError());
                            return;
                        case CHCNetSDK.NET_SDK_CONFIG_STATUS_NEED_WAIT:
                            Console.WriteLine("配置等待");
                            Thread.Sleep(10);
                            continue;
                        case CHCNetSDK.NET_SDK_CONFIG_STATUS_FAILED:
                            string failedCardNo = Encoding.Default.GetString(cardStatus.byCardNo).Trim();
                            string failedDesc = EnumHelper.GetErrorDescription((int)cardStatus.dwErrorCode);
                            Console.WriteLine("删除卡失败, 卡号: " + failedCardNo + ", 错误信息:" + failedDesc);
                            break;
                        case CHCNetSDK.NET_SDK_CONFIG_STATUS_EXCEPTION:
                            string exceptionCardNo = Encoding.Default.GetString(cardStatus.byCardNo).Trim();
                            string exceptionDesc = EnumHelper.GetErrorDescription((int)cardStatus.dwErrorCode);
                            Console.WriteLine("删除卡异常, 卡号: " + exceptionCardNo + ", 错误信息:" + exceptionDesc);
                            break;
                        case CHCNetSDK.NET_SDK_CONFIG_STATUS_SUCCESS:
                            if (cardStatus.dwErrorCode != 0)
                            {
                                string CardNo = Encoding.Default.GetString(cardStatus.byCardNo).Trim();
                                string errorDesc = EnumHelper.GetErrorDescription((int)cardStatus.dwErrorCode);
                                Console.WriteLine("删除卡成功,但是错误码信息： " + errorDesc + ", 卡号：" + CardNo);
                            }
                            else
                            {
                                Console.WriteLine("删除卡成功, 卡号: " + cardNo + ", 状态：" + cardStatus.byStatus);
                            }
                            continue;
                        case CHCNetSDK.NET_SDK_CONFIG_STATUS_FINISH:
                            Console.WriteLine("删除卡完成");
                            break;
                        default:
                            Console.WriteLine("未知状态码: " + state);
                            return;
                    }
                    break;
                }
                if (!CHCNetSDK.NET_DVR_StopRemoteConfig(configHandle))
                {
                    Console.WriteLine("NET_DVR_StopRemoteConfig接口调用失败，错误码：" + CHCNetSDK.NET_DVR_GetLastError());
                }
                else
                {
                    Console.WriteLine("NET_DVR_StopRemoteConfig接口成功\n");
                }
            }
            finally
            {
                Marshal.FreeHGlobal(ptrCardCond);
            }
        }

        public static void CleanCardInfo(int lUserID)
        {
            var paramType = new CHCNetSDK.NET_DVR_ACS_PARAM_TYPE
            {
                dwSize = (uint)Marshal.SizeOf(typeof(CHCNetSDK.NET_DVR_ACS_PARAM_TYPE)),
                dwParamType = CHCNetSDK.ACS_PARAM_CARD,
                wLocalControllerID = 0
            };
            IntPtr ptrParamType = Marshal.AllocHGlobal(Marshal.SizeOf(paramType));
            try
            {
                Marshal.StructureToPtr(paramType, ptrParamType, false);
                bool result = CHCNetSDK.NET_DVR_RemoteControl(
                lUserID,
                CHCNetSDK.NET_DVR_CLEAR_ACS_PARAM,
                ptrParamType,
                (int)paramType.dwSize
                );
                if (!result)
                {
                    Console.WriteLine("清空卡号错误，错误码为" + CHCNetSDK.NET_DVR_GetLastError());
                    return;
                }
                Console.WriteLine("清空卡号成功");
            }
            finally
            {
                Marshal.FreeHGlobal(ptrParamType);
            }
        }

        public static void SetCardTemplate(int lUserID, int iPlanTemplateNumber)
        {
            var planCond = new CHCNetSDK.NET_DVR_PLAN_TEMPLATE_COND
            {
                dwSize = (uint)Marshal.SizeOf(typeof(CHCNetSDK.NET_DVR_PLAN_TEMPLATE_COND)),
                dwPlanTemplateNumber = (uint)iPlanTemplateNumber,
                wLocalControllerID = 0
            };

            var planTemCfg = new CHCNetSDK.NET_DVR_PLAN_TEMPLATE();
            planTemCfg.Init();
            planTemCfg.dwSize = (uint)Marshal.SizeOf(typeof(CHCNetSDK.NET_DVR_PLAN_TEMPLATE));
            planTemCfg.byEnable = 1;
            planTemCfg.dwWeekPlanNo = 2;
            for (int i = 0; i < planTemCfg.dwHolidayGroupNo.Length; i++)
            {
                planTemCfg.dwHolidayGroupNo[i] = 0;
            }
            try
            {
                byte[] templateNameBytes = Encoding.GetEncoding("GBK").GetBytes("CardTemplatePlan_2");
                Array.Clear(planTemCfg.byTemplateName, 0, planTemCfg.byTemplateName.Length);
                Array.Copy(templateNameBytes, planTemCfg.byTemplateName, Math.Min(templateNameBytes.Length, planTemCfg.byTemplateName.Length));
            }
            catch (Exception ex)
            {
                Console.WriteLine("设置模板名称失败: " + ex.Message);
                return;
            }
            IntPtr ptrPlanCond = Marshal.AllocHGlobal(Marshal.SizeOf(planCond));
            IntPtr ptrPlanTemCfg = Marshal.AllocHGlobal(Marshal.SizeOf(planTemCfg));
            IntPtr pInt = Marshal.AllocHGlobal(sizeof(int));

            try
            {
                Marshal.StructureToPtr(planCond, ptrPlanCond, false);
                Marshal.StructureToPtr(planTemCfg, ptrPlanTemCfg, false);
                Marshal.WriteInt32(pInt, 0);
                if (!CHCNetSDK.NET_DVR_SetDeviceConfig(
                    lUserID,
                    (uint)CHCNetSDK.NET_DVR_SET_CARD_RIGHT_PLAN_TEMPLATE_V50,
                    1u,
                    ptrPlanCond,
                    (uint)planCond.dwSize,
                    pInt,
                    ptrPlanTemCfg,
                    (uint)planTemCfg.dwSize))
                {
                    Console.WriteLine("NET_DVR_SET_CARD_RIGHT_PLAN_TEMPLATE_V50失败，错误号：" + CHCNetSDK.NET_DVR_GetLastError());
                    return;
                }
                Console.WriteLine("NET_DVR_SET_CARD_RIGHT_PLAN_TEMPLATE_V50成功！");

                // 获取卡权限周计划参数
                var weekPlanCond = new CHCNetSDK.NET_DVR_WEEK_PLAN_COND
                {
                    dwSize = (uint)Marshal.SizeOf(typeof(CHCNetSDK.NET_DVR_WEEK_PLAN_COND)),
                    dwWeekPlanNumber = 2,
                    wLocalControllerID = 0
                };

                var weekPlanCfg = new CHCNetSDK.NET_DVR_WEEK_PLAN_CFG
                {
                    dwSize = (uint)Marshal.SizeOf(typeof(CHCNetSDK.NET_DVR_WEEK_PLAN_CFG))
                };
                IntPtr ptrWeekPlanCond = Marshal.AllocHGlobal(Marshal.SizeOf(weekPlanCond));
                IntPtr ptrWeekPlanCfg = Marshal.AllocHGlobal(Marshal.SizeOf(weekPlanCfg));
                try
                {
                    Marshal.StructureToPtr(weekPlanCond, ptrWeekPlanCond, false);
                    Marshal.StructureToPtr(weekPlanCfg, ptrWeekPlanCfg, false);
                    if (!CHCNetSDK.NET_DVR_GetDeviceConfig(
                    lUserID,
                    (uint)CHCNetSDK.NET_DVR_GET_CARD_RIGHT_WEEK_PLAN_V50,
                    1u,
                    ptrWeekPlanCond,
                    weekPlanCond.dwSize,
                    pInt,
                    ptrWeekPlanCfg,
                    weekPlanCfg.dwSize))
                    {
                        Console.WriteLine("NET_DVR_GET_CARD_RIGHT_WEEK_PLAN_V50失败，错误号：" + CHCNetSDK.NET_DVR_GetLastError());
                        return;
                    }
                    weekPlanCfg = (CHCNetSDK.NET_DVR_WEEK_PLAN_CFG)Marshal.PtrToStructure(
                        ptrWeekPlanCfg, typeof(CHCNetSDK.NET_DVR_WEEK_PLAN_CFG));

                    // 设置为一周7天，每天14:00-16:00有效
                    weekPlanCfg.byEnable = 1;

                    const int MAX_DAYS = 7;
                    const int MAX_TIMESEGMENT_PER_DAY = 8;
                    // 初始化所有时间段（一维数组遍历）
                    for (int dayIndex = 0; dayIndex < MAX_DAYS; dayIndex++)
                    {
                        for (int segmentIndex = 0; segmentIndex < MAX_TIMESEGMENT_PER_DAY; segmentIndex++)
                        {
                            int index = dayIndex * MAX_TIMESEGMENT_PER_DAY + segmentIndex;
                            weekPlanCfg.struPlanCfg[index].byEnable = 0;
                            weekPlanCfg.struPlanCfg[index].struTimeSegment.struBeginTime.byHour = 0;
                            weekPlanCfg.struPlanCfg[index].struTimeSegment.struBeginTime.byMinute = 0;
                            weekPlanCfg.struPlanCfg[index].struTimeSegment.struBeginTime.bySecond = 0;
                            weekPlanCfg.struPlanCfg[index].struTimeSegment.struEndTime.byHour = 0;
                            weekPlanCfg.struPlanCfg[index].struTimeSegment.struEndTime.byMinute = 0;
                            weekPlanCfg.struPlanCfg[index].struTimeSegment.struEndTime.bySecond = 0;
                        }
                    }

                    // 设置一周7天，每天14:00-16:00（第一个时间段）
                    for (int dayIndex = 0; dayIndex < MAX_DAYS; dayIndex++)
                    {
                        int index = dayIndex * MAX_TIMESEGMENT_PER_DAY;
                        weekPlanCfg.struPlanCfg[index].byEnable = 1;
                        weekPlanCfg.struPlanCfg[index].struTimeSegment.struBeginTime.byHour = 14;
                        weekPlanCfg.struPlanCfg[index].struTimeSegment.struBeginTime.byMinute = 0;
                        weekPlanCfg.struPlanCfg[index].struTimeSegment.struBeginTime.bySecond = 0;
                        weekPlanCfg.struPlanCfg[index].struTimeSegment.struEndTime.byHour = 16;
                        weekPlanCfg.struPlanCfg[index].struTimeSegment.struEndTime.byMinute = 0;
                        weekPlanCfg.struPlanCfg[index].struTimeSegment.struEndTime.bySecond = 0;
                    }
                    Marshal.StructureToPtr(weekPlanCfg, ptrWeekPlanCfg, true);

                    // 设置卡权限周计划参数
                    if (!CHCNetSDK.NET_DVR_SetDeviceConfig(
                        lUserID,
                        (uint)CHCNetSDK.NET_DVR_SET_CARD_RIGHT_WEEK_PLAN_V50,
                        1u,
                        ptrWeekPlanCond,
                        weekPlanCond.dwSize,
                        pInt,
                        ptrWeekPlanCfg,
                        weekPlanCfg.dwSize))
                    {
                        Console.WriteLine("NET_DVR_SET_CARD_RIGHT_WEEK_PLAN_V50失败，错误号：" + CHCNetSDK.NET_DVR_GetLastError());
                    }
                    else
                    {
                        Console.WriteLine("NET_DVR_SET_CARD_RIGHT_WEEK_PLAN_V50成功！");
                    }
                }
                finally
                {
                    Marshal.FreeHGlobal(ptrWeekPlanCond);
                    Marshal.FreeHGlobal(ptrWeekPlanCfg);
                }
            }
            finally
            {
                Marshal.FreeHGlobal(ptrPlanCond);
                Marshal.FreeHGlobal(ptrPlanTemCfg);
                Marshal.FreeHGlobal(pInt);
            }
        }
    }
}
