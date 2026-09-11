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
    class EventSearch
    {
        public static void SearchAllEvent(int lUserID)
        {
            int i = 0; // 事件条数计数器
            var struAcsEventCond = new CHCNetSDK.NET_DVR_ACS_EVENT_COND
            {
                dwSize = (uint)Marshal.SizeOf(typeof(CHCNetSDK.NET_DVR_ACS_EVENT_COND)),
                dwMajor = 0,
                dwMinor = 0,
                struStartTime = new CHCNetSDK.NET_DVR_TIME
                {
                    dwYear = 2025,
                    dwMonth = 1,
                    dwDay = 1,
                    dwHour = 0,
                    dwMinute = 0,
                    dwSecond = 0
                },
                struEndTime = new CHCNetSDK.NET_DVR_TIME
                {
                    dwYear = 2025,
                    dwMonth = 1,
                    dwDay = 1,
                    dwHour = 12,
                    dwMinute = 0,
                    dwSecond = 0
                },
                wInductiveEventType = 1,
                byPicEnable = 1,
                byRes = new byte[101]
            };
            struAcsEventCond.Init();
            IntPtr ptrStruEventCond = Marshal.AllocHGlobal(Marshal.SizeOf(struAcsEventCond));
            Marshal.StructureToPtr(struAcsEventCond, ptrStruEventCond, false);
            int m_lSearchEventHandle = CHCNetSDK.NET_DVR_StartRemoteConfig(
                lUserID,
                CHCNetSDK.NET_DVR_GET_ACS_EVENT,
                ptrStruEventCond,
                (uint)Marshal.SizeOf(typeof(CHCNetSDK.NET_DVR_ACS_EVENT_COND)),
                null,
                IntPtr.Zero);
            if (m_lSearchEventHandle <= -1)
            {
                Console.WriteLine("NET_DVR_StartRemoteConfig调用失败，错误码: " + CHCNetSDK.NET_DVR_GetLastError());
                Marshal.FreeHGlobal(ptrStruEventCond);
                return;
            }
            CHCNetSDK.NET_DVR_ACS_EVENT_CFG struAcsEventCfg = new CHCNetSDK.NET_DVR_ACS_EVENT_CFG
            {
                dwSize = (uint)Marshal.SizeOf(typeof(CHCNetSDK.NET_DVR_ACS_EVENT_CFG)),
                sNetUser = new byte[CHCNetSDK.MAX_NAMELEN],
                struRemoteHostAddr = new CHCNetSDK.NET_DVR_IPADDR(),
                struAcsEventInfo = new CHCNetSDK.NET_DVR_ACS_EVENT_DETAIL(),
                pPicData = IntPtr.Zero,
                pQRCodeInfo = IntPtr.Zero,
                pVisibleLightData = IntPtr.Zero,
                pThermalData = IntPtr.Zero,
                byRes = new byte[36]
            };
            struAcsEventCfg.init();
            IntPtr ptrStruEventCfg = Marshal.AllocHGlobal(Marshal.SizeOf(struAcsEventCfg));
            Marshal.StructureToPtr(struAcsEventCfg, ptrStruEventCfg, false);
            while (true)
            {
                Console.WriteLine("i=" + i);
                int dwEventSearch = CHCNetSDK.NET_DVR_GetNextRemoteConfig(
                m_lSearchEventHandle,
                ptrStruEventCfg,
                Marshal.SizeOf(typeof(CHCNetSDK.NET_DVR_ACS_EVENT_CFG)));
                if (dwEventSearch <= -1)
                {
                    Console.WriteLine("NET_DVR_GetNextRemoteConfig接口调用失败，错误码: " + CHCNetSDK.NET_DVR_GetLastError());
                    break;
                }
                if (dwEventSearch == CHCNetSDK.NET_SDK_GET_NEXT_STATUS_NEED_WAIT)
                {
                    Console.WriteLine("配置等待....");
                    Thread.Sleep(10);
                    continue;
                }
                else if (dwEventSearch == CHCNetSDK.NET_SDK_NEXT_STATUS__FINISH)
                {
                    Console.WriteLine("获取事件完成");
                    break;
                }
                else if (dwEventSearch == CHCNetSDK.NET_SDK_GET_NEXT_STATUS_FAILED)
                {
                    Console.WriteLine("获取事件出现异常");
                    break;
                }
                else if (dwEventSearch == CHCNetSDK.NET_SDK_GET_NEXT_STATUS_SUCCESS)
                {
                    struAcsEventCfg = (CHCNetSDK.NET_DVR_ACS_EVENT_CFG)Marshal.PtrToStructure(
                        ptrStruEventCfg,
                        typeof(CHCNetSDK.NET_DVR_ACS_EVENT_CFG));
                    // 转换卡号为字符串
                    string cardNo = Encoding.ASCII.GetString(struAcsEventCfg.struAcsEventInfo.byCardNo)
                        .TrimEnd('\0');
                    Console.WriteLine(i + " 获取事件成功, " +
                        "报警主类型: 0x" + struAcsEventCfg.dwMajor.ToString("X") + ", " +
                        "报警次类型: 0x" + struAcsEventCfg.dwMinor.ToString("X") + ", " +
                        "卡号: " + cardNo);
                    Console.WriteLine("梯控楼层编号: " + struAcsEventCfg.struAcsEventInfo.dwDoorNo);
                    // 人脸图片保存
                    if (struAcsEventCfg.dwPicDataLen > 0 && struAcsEventCfg.pPicData != IntPtr.Zero)
                    {
                        try
                        {
                            string directory = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "pic");
                            if (!Directory.Exists(directory))
                            {
                                Directory.CreateDirectory(directory);
                            }
                            string filename = Path.Combine(directory, i + "_event.jpg");
                            byte[] buffer = new byte[struAcsEventCfg.dwPicDataLen];
                            Marshal.Copy(struAcsEventCfg.pPicData, buffer, 0, buffer.Length);
                            File.WriteAllBytes(filename, buffer);
                            Console.WriteLine("图片已保存至: " + filename);
                        }
                        catch (Exception ex)
                        {
                            Console.WriteLine("保存图片时出错: " + ex.Message);
                        }
                    }
                    i++;
                }
            }
            Marshal.FreeHGlobal(ptrStruEventCond);
            Marshal.FreeHGlobal(ptrStruEventCfg);
            if (!CHCNetSDK.NET_DVR_StopRemoteConfig(m_lSearchEventHandle))
            {
                Console.WriteLine("NET_DVR_StopRemoteConfig接口调用失败，错误码: " + CHCNetSDK.NET_DVR_GetLastError());
            }
            else
            {
                Console.WriteLine("NET_DVR_StopRemoteConfig接口成功");
            }
        }
    }
}
