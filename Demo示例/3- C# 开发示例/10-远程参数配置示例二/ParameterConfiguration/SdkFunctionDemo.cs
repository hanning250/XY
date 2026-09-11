using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Runtime.InteropServices;
using ParameterConfiguration.Common;
using System.Threading;

namespace ParameterConfiguration
{
    class SdkFunctionDemo
    {
        private static CHCNetSDK.RemoteConfigCallback m_StateCallback = null;
        public const int IPCHANNEL1 = 1;
        public static bool bStopFlag = false;

        public static void GetDeviceCFG(int lUserID)
        {
            CHCNetSDK.NET_DVR_DEVICECFG_V40 struDeviceCfg = new CHCNetSDK.NET_DVR_DEVICECFG_V40();
            struDeviceCfg.sDVRName = new byte[64]; // 初始化设备名称数组
            UInt32 dwReturn = 0;
            Int32 nSize = Marshal.SizeOf(struDeviceCfg);
            IntPtr ptrDeviceCfg = Marshal.AllocHGlobal(nSize);
            Marshal.StructureToPtr(struDeviceCfg, ptrDeviceCfg, false);
            // 调用NET_DVR_GetDVRConfig获取设备配置
            if (!CHCNetSDK.NET_DVR_GetDVRConfig(lUserID, CHCNetSDK.NET_DVR_GET_DEVICECFG_V40, 0xFFFFFF, ptrDeviceCfg, (UInt32)nSize, ref dwReturn))
            {
                // 获取配置失败，输出错误码
                Console.WriteLine("Get device config error, {0}", CHCNetSDK.NET_DVR_GetLastError());
            }
            else
            {
                // 获取配置成功，可以在这里处理struDeviceCfg结构体中的数据
                Console.WriteLine("Get device config success.");
                struDeviceCfg = (CHCNetSDK.NET_DVR_DEVICECFG_V40)Marshal.PtrToStructure(ptrDeviceCfg, typeof(CHCNetSDK.NET_DVR_DEVICECFG_V40));
                // 示例：输出设备名称
                string deviceName = System.Text.Encoding.ASCII.GetString(struDeviceCfg.sDVRName).TrimEnd('\0');
                Console.WriteLine("Device name: {0}", deviceName);

                // 输出设备固件版本
                PrintSoftwareBuildDate(struDeviceCfg.dwSoftwareBuildDate);

                Console.WriteLine("Alarm In Port Num: {0}", struDeviceCfg.byAlarmInPortNum);
                Console.WriteLine("Alarm Out Port Num: {0}", struDeviceCfg.byAlarmOutPortNum);
                Console.WriteLine("Disk Num: {0}", struDeviceCfg.byDiskNum);
                Console.WriteLine("Channel Num: {0}", struDeviceCfg.byChanNum);
                Console.WriteLine("IP Channel Num: {0}", struDeviceCfg.byIPChanNum);
            }
        }

        // 输出设备固件版本
        public static void PrintSoftwareBuildDate(uint dwDate)
        {
            // 提取年、月、日
            int year = (int)((dwDate >> 16) & 0xFFFF); // 高16位表示年份
            int month = (int)((dwDate >> 8) & 0xFF);   // 次高8位表示月份
            int day = (int)(dwDate & 0xFF);          // 低8位表示日期


            year += 2000;

            // 打印日期
            Console.WriteLine("Software Build Date: {0:0000}-{1:00}-{2:00}", year, month, day);
        }

        public static void GetAndSetDeviceTime(int lUserID)
        {
            //获取设备时间
            CHCNetSDK.NET_DVR_TIME struDeviceTime = new CHCNetSDK.NET_DVR_TIME();


            UInt32 dwReturn = 0;
            Int32 nSize = Marshal.SizeOf(struDeviceTime);
            IntPtr ptrDeviceTime = Marshal.AllocHGlobal(nSize);
            Marshal.StructureToPtr(struDeviceTime, ptrDeviceTime, false);
            // 调用NET_DVR_GetDVRConfig获取设备配置
            if (!CHCNetSDK.NET_DVR_GetDVRConfig(lUserID, CHCNetSDK.NET_DVR_GET_TIMECFG, 0xFFFFFF, ptrDeviceTime, (UInt32)nSize, ref dwReturn))
            {
                // 获取配置失败，输出错误码
                Console.WriteLine("Get device config error, {0}", CHCNetSDK.NET_DVR_GetLastError());
            }
            else
            {
                // 获取配置成功，可以在这里处理结构体中的数据
                Console.WriteLine("Get device config success.");
                struDeviceTime = (CHCNetSDK.NET_DVR_TIME)Marshal.PtrToStructure(ptrDeviceTime, typeof(CHCNetSDK.NET_DVR_TIME));

                Console.WriteLine("Year: {0}", struDeviceTime.dwYear);
                Console.WriteLine("Month: {0}", struDeviceTime.dwMonth);
                Console.WriteLine("Day: {0}", struDeviceTime.dwMonth);
                Console.WriteLine("Hour: {0}", struDeviceTime.dwHour);
                Console.WriteLine("Minute: {0}", struDeviceTime.dwMinute);
                Console.WriteLine("Second: {0}", struDeviceTime.dwSecond);
            }

            // 调用NET_DVR_SetDVRConfig设置配置
            if (!CHCNetSDK.NET_DVR_SetDVRConfig(lUserID, CHCNetSDK.NET_DVR_SET_TIMECFG, 0xFFFFFF, ptrDeviceTime, (UInt32)nSize))
            {
                // 获取配置失败，输出错误码
                Console.WriteLine("Set device config error, {0}", CHCNetSDK.NET_DVR_GetLastError());
            }
            else
            {
                Console.WriteLine("Set device config success.");
            }
        }

        //获取和设置图像参数
        public static void GetAndSetDevicePicCfg(int lUserID)
        {
            //获取设备图像参数
            CHCNetSDK.NET_DVR_PICCFG_V40 struDevicePicCfg = new CHCNetSDK.NET_DVR_PICCFG_V40();

            UInt32 dwReturn = 0;
            Int32 nSize = Marshal.SizeOf(struDevicePicCfg);
            IntPtr ptrDevicePicCfg = Marshal.AllocHGlobal(nSize);
            Marshal.StructureToPtr(struDevicePicCfg, ptrDevicePicCfg, false);
            // 调用NET_DVR_SetDVRConfig设置配置
            if (!CHCNetSDK.NET_DVR_GetDVRConfig(lUserID, CHCNetSDK.NET_DVR_GET_PICCFG_V40, IPCHANNEL1, ptrDevicePicCfg, (UInt32)nSize, ref dwReturn))
            {
                // 获取配置失败，输出错误码
                Console.WriteLine("Get device config error, {0}", CHCNetSDK.NET_DVR_GetLastError());
            }
            else
            {
                // 获取配置成功，可以在这里处理struDeviceCfg结构体中的数据
                Console.WriteLine("Get device config success.");
                struDevicePicCfg = (CHCNetSDK.NET_DVR_PICCFG_V40)Marshal.PtrToStructure(ptrDevicePicCfg, typeof(CHCNetSDK.NET_DVR_PICCFG_V40));

                Console.WriteLine("ShowOsd: {0}", struDevicePicCfg.dwShowOsd);//预览的图象上是否显示OSD：0-不显示，1-显示（区域大小704*576） 
            }

            // 调用NET_DVR_SetDVRConfig设置配置
            if (!CHCNetSDK.NET_DVR_SetDVRConfig(lUserID, CHCNetSDK.NET_DVR_SET_PICCFG_V40, IPCHANNEL1, ptrDevicePicCfg, (UInt32)nSize))
            {
                // 获取配置失败，输出错误码
                Console.WriteLine("Set device config error, {0}", CHCNetSDK.NET_DVR_GetLastError());
            }
            else
            {
                // 获取配置成功，可以在这里处理struDeviceCfg结构体中的数据
                Console.WriteLine("Set device config success.");


            }

        }

        //获取和设置录像计划参数
        public static void GetAndSetDeviceRecordCfg(int lUserID)
        {
            //获取设备录像计划参数
            CHCNetSDK.NET_DVR_RECORD_V40 struDeviceRecordCfg = new CHCNetSDK.NET_DVR_RECORD_V40();


            UInt32 dwReturn = 0;
            Int32 nSize = Marshal.SizeOf(struDeviceRecordCfg);
            IntPtr ptrDeviceRecordCfg = Marshal.AllocHGlobal(nSize);
            Marshal.StructureToPtr(struDeviceRecordCfg, ptrDeviceRecordCfg, false);
            // 调用NET_DVR_GetDVRConfig获取设备配置
            if (!CHCNetSDK.NET_DVR_GetDVRConfig(lUserID, CHCNetSDK.NET_DVR_GET_RECORDCFG_V40, 33, ptrDeviceRecordCfg, (UInt32)nSize, ref dwReturn))
            {
                // 获取配置失败，输出错误码
                Console.WriteLine("Get device config error, {0}", CHCNetSDK.NET_DVR_GetLastError());
            }
            else
            {
                // 获取配置成功，可以在这里处理结构体中的数据
                Console.WriteLine("Get device config success.");
                struDeviceRecordCfg = (CHCNetSDK.NET_DVR_RECORD_V40)Marshal.PtrToStructure(ptrDeviceRecordCfg, typeof(CHCNetSDK.NET_DVR_RECORD_V40));

                Console.WriteLine("Record: {0}", struDeviceRecordCfg.dwRecord);//是否启用计划录像配置：0-否，1-是  
            }

            //设置设备录像计划参数
            // 调用NET_DVR_SetDVRConfig设置配置
            if (!CHCNetSDK.NET_DVR_SetDVRConfig(lUserID, CHCNetSDK.NET_DVR_SET_RECORDCFG_V40, 33, ptrDeviceRecordCfg, (UInt32)nSize))
            {
                // 获取配置失败，输出错误码
                Console.WriteLine("Set device config error, {0}", CHCNetSDK.NET_DVR_GetLastError());
            }
            else
            {
                // 获取配置成功，可以在这里处理结构体中的数据
                Console.WriteLine("Set device config success.");
            }
      }



        //获取和设置前端扩展参数
        public static void GetAndSetDeviceCcpdaramCfg(int lUserID)
        {
            //获取和设置网络参数
            CHCNetSDK.NET_DVR_CAMERAPARAMCFG_EX struDeviceCcpdaramCfg = new CHCNetSDK.NET_DVR_CAMERAPARAMCFG_EX();

            UInt32 dwReturn = 0;
            Int32 nSize = Marshal.SizeOf(struDeviceCcpdaramCfg);
            IntPtr ptrDeviceCcpdaramCfg = Marshal.AllocHGlobal(nSize);
            Marshal.StructureToPtr(struDeviceCcpdaramCfg, ptrDeviceCcpdaramCfg, false);
            // 调用NET_DVR_GetDVRConfig获取设备配置
            if (!CHCNetSDK.NET_DVR_GetDVRConfig(lUserID, CHCNetSDK.NET_DVR_GET_CCDPARAMCFG_EX, IPCHANNEL1, ptrDeviceCcpdaramCfg, (UInt32)nSize, ref dwReturn))
            {
                // 获取配置失败，输出错误码
                Console.WriteLine("Get device config error, {0}", CHCNetSDK.NET_DVR_GetLastError());
            }
            else
            {
                // 获取配置成功，可以在这里处理结构体中的数据
                Console.WriteLine("Get device config success.");
                struDeviceCcpdaramCfg = (CHCNetSDK.NET_DVR_CAMERAPARAMCFG_EX)Marshal.PtrToStructure(ptrDeviceCcpdaramCfg, typeof(CHCNetSDK.NET_DVR_CAMERAPARAMCFG_EX)); 
            }
            //设置前端扩展参数          
            // 调用NET_DVR_SetDVRConfig设置配置
            if (!CHCNetSDK.NET_DVR_SetDVRConfig(lUserID, CHCNetSDK.NET_DVR_SET_CCDPARAMCFG_EX, IPCHANNEL1, ptrDeviceCcpdaramCfg, (UInt32)nSize))
            {
                // 获取配置失败，输出错误码
                Console.WriteLine("Set device config error, {0}", CHCNetSDK.NET_DVR_GetLastError());
            }
            else
            {
                // 获取配置成功，可以在这里处理结构体中的数据
                Console.WriteLine("Set device config success.");
            }
        }


        //获取和设置网络参数
        public static void GetAndSetDeviceNetCfg(int lUserID)
        {
            //获取和设置网络参数
            CHCNetSDK.NET_DVR_NETCFG_V50 struDeviceNetCfg = new CHCNetSDK.NET_DVR_NETCFG_V50();
            UInt32 dwReturn = 0;
            Int32 nSize = Marshal.SizeOf(struDeviceNetCfg);
            IntPtr ptrDeviceNetCfg = Marshal.AllocHGlobal(nSize);
            Marshal.StructureToPtr(struDeviceNetCfg, ptrDeviceNetCfg, false);
            // 调用NET_DVR_GetDVRConfig获取设备配置
            if (!CHCNetSDK.NET_DVR_GetDVRConfig(lUserID, CHCNetSDK.NET_DVR_GET_NETCFG_V50, IPCHANNEL1, ptrDeviceNetCfg, (UInt32)nSize, ref dwReturn))
            {
                // 获取配置失败，输出错误码
                Console.WriteLine("Get device config error, {0}", CHCNetSDK.NET_DVR_GetLastError());
            }
            else
            {
                // 获取配置成功，可以在这里处理结构体中的数据
                Console.WriteLine("Get device config success.");
                struDeviceNetCfg = (CHCNetSDK.NET_DVR_NETCFG_V50)Marshal.PtrToStructure(ptrDeviceNetCfg, typeof(CHCNetSDK.NET_DVR_NETCFG_V50));
            }

            // 调用NET_DVR_SetDVRConfig设置配置
            if (!CHCNetSDK.NET_DVR_SetDVRConfig(lUserID, CHCNetSDK.NET_DVR_SET_NETCFG_V50, IPCHANNEL1, ptrDeviceNetCfg, (UInt32)nSize))
            {
                // 获取配置失败，输出错误码
                Console.WriteLine("Set device config error, {0}", CHCNetSDK.NET_DVR_GetLastError());
            }
            else
            {
                // 获取配置成功，可以在这里处理结构体中的数据
                Console.WriteLine("Set device config success.");
            }
        }
        
        //获取获取IP接入配置参数
        public static void GetDeviceIpparaCfg(int lUserID)
        {
            //获取获取IP接入配置参数
            CHCNetSDK.NET_DVR_IPPARACFG_V40 struDeviceWorkStatus = new CHCNetSDK.NET_DVR_IPPARACFG_V40();
            UInt32 dwReturn = 0;
            Int32 nSize = Marshal.SizeOf(struDeviceWorkStatus);
            struDeviceWorkStatus.dwSize = (uint)nSize;
            IntPtr ptrDeviceIpparaCfg = Marshal.AllocHGlobal(nSize);
            Marshal.StructureToPtr(struDeviceWorkStatus, ptrDeviceIpparaCfg, false);
            // 调用NET_DVR_GetDVRConfig获取设备配置
            if (!CHCNetSDK.NET_DVR_GetDVRConfig(lUserID, CHCNetSDK.NET_DVR_GET_IPPARACFG_V40, 0, ptrDeviceIpparaCfg, (uint)nSize, ref dwReturn))
            {
                // 获取配置失败，输出错误码
                Console.WriteLine("Get device config error, {0}", CHCNetSDK.NET_DVR_GetLastError());
            }
            else
            {
                // 获取配置成功，可以在这里处理结构体中的数据
                Console.WriteLine("Get device config success.");
                struDeviceWorkStatus = (CHCNetSDK.NET_DVR_IPPARACFG_V40)Marshal.PtrToStructure(ptrDeviceIpparaCfg, typeof(CHCNetSDK.NET_DVR_GETWORKSTATE_COND));
            }
        }

        //回调函数 获取设备工作状态
        public static void RemoteConfigCallback(uint dwType, IntPtr lpBuffer, uint dwBufLen, IntPtr pUserData)
        {
            if (dwType == (uint)CHCNetSDK.NET_SDK_CALLBACK_TYPE.NET_SDK_CALLBACK_TYPE_STATUS)
            {
                int dwStatus = Marshal.ReadInt32(lpBuffer);
                if (dwStatus == (uint)CHCNetSDK.NET_SDK_CALLBACK_STATUS_NORMAL.NET_SDK_CALLBACK_STATUS_SUCCESS)
                {
                    Console.WriteLine("SUCCESS");
                    bStopFlag = true;
                }
                else if (dwStatus == (uint)CHCNetSDK.NET_SDK_CALLBACK_STATUS_NORMAL.NET_SDK_CALLBACK_STATUS_PROCESSING)
                {
                    Console.WriteLine("PROCESSING...");
                }
                else if (dwStatus == (uint)CHCNetSDK.NET_SDK_CALLBACK_STATUS_NORMAL.NET_SDK_CALLBACK_STATUS_FAILED)
                {

                    int InitpBuffer = 4;
                    int pBufferTemp = 0;

                    pBufferTemp = Marshal.ReadInt32(lpBuffer, InitpBuffer);
                    if (pBufferTemp != 0)
                    {
                        Console.WriteLine("下发失败,错误码： dwStatus:" + pBufferTemp);
                    }
                    bStopFlag = true;
                }
                else if (dwStatus == (uint)CHCNetSDK.NET_SDK_CALLBACK_STATUS_NORMAL.NET_SDK_CALLBACK_STATUS_EXCEPTION)
                {
                    Console.WriteLine("获取异常");
                    bStopFlag = true;
                }
            }
            else if (dwType == (uint)CHCNetSDK.NET_SDK_CALLBACK_TYPE.NET_SDK_CALLBACK_TYPE_DATA)
            {
                CHCNetSDK.NET_DVR_WORKSTATE_V40 struDeviceWorkStatue = new CHCNetSDK.NET_DVR_WORKSTATE_V40();

                struDeviceWorkStatue = (CHCNetSDK.NET_DVR_WORKSTATE_V40)Marshal.PtrToStructure(lpBuffer, typeof(CHCNetSDK.NET_DVR_WORKSTATE_V40));
                Console.WriteLine("Get devicestate, {0}", struDeviceWorkStatue.dwDeviceStatic);
                return;
            }
            return;
        }

        public static void GetDeviceWorkStatus(int lUserID)
        {
            //获取获取设备工作状态
            CHCNetSDK.NET_DVR_GETWORKSTATE_COND struDeviceWorkStatus = new CHCNetSDK.NET_DVR_GETWORKSTATE_COND();            
            Int32 nSize = Marshal.SizeOf(struDeviceWorkStatus);
            struDeviceWorkStatus.dwSize = (UInt32)nSize;
            IntPtr ptrDeviceWorkState = Marshal.AllocHGlobal(nSize);
            Marshal.StructureToPtr(struDeviceWorkStatus, ptrDeviceWorkState, false);            

            //设置回调函数
            if (m_StateCallback == null)
            {
                m_StateCallback = new CHCNetSDK.RemoteConfigCallback(RemoteConfigCallback);
            }

            int iHandle = CHCNetSDK.NET_DVR_StartRemoteConfig(lUserID, CHCNetSDK.NET_DVR_GET_WORK_STATUS_V50, ptrDeviceWorkState, nSize, m_StateCallback, IntPtr.Zero);

            if (iHandle < 0)
            {
                Console.WriteLine("NET_DVR_GET_WORK_STATUS_V50 failed, error:" + CHCNetSDK.NET_DVR_GetLastError());
                return;
            }
            else
            {
                Console.WriteLine("NET_DVR_GET_WORK_STATUS_V50 succ");
            }
            Thread.Sleep(2000);
            CHCNetSDK.NET_DVR_StopRemoteConfig(iHandle);
        }

        public static void GetDeviceJpegAbility(int lUserID)
        {
            string xml = "<JpegCaptureAbility version=\"2.0\"> /r/n" +
                        "<channelNO>1</channelNO>/r/n" +
                        "</JpegCaptureAbility>/r/n";
            // 将字符串转换为字节数组
            byte[] bytes = System.Text.Encoding.UTF8.GetBytes(xml);
            uint nSize = (uint)bytes.Length;
            // 分配非托管内存
            IntPtr ptr = Marshal.AllocHGlobal(bytes.Length);
            uint Nsizeptr2 = 10000;
            IntPtr ptr2 = Marshal.AllocHGlobal(10000);
            bool iHandle = CHCNetSDK.NET_DVR_GetDeviceAbility(lUserID, CHCNetSDK.DEVICE_JPEG_CAP_ABILITY, IntPtr.Zero, 0, ptr2, Nsizeptr2);

            if (iHandle == false)
            {
                Console.WriteLine("NET_DVR_GET_WORK_STATUS_V50 failed, error:" + CHCNetSDK.NET_DVR_GetLastError());
                return;
            }
            else
            {
                Console.WriteLine("NET_DVR_GET_WORK_STATUS_V50 succ");
                // 从非托管内存转换回字符串
                string managedString = Marshal.PtrToStringAnsi(ptr2);

                // 打印转换回来的字符串
                Console.WriteLine(managedString);
            }
        }


        public static void GetDeviceSoftAbility(int lUserID)
        {
            string xml = "<JpegCaptureAbility version=\"2.0\"> /r/n" +
                        "<channelNO>1</channelNO>/r/n" +
                        "</JpegCaptureAbility>/r/n";
            // 将字符串转换为字节数组
            byte[] bytes = System.Text.Encoding.UTF8.GetBytes(xml);
            uint nSize = (uint)bytes.Length;
            // 分配非托管内存
            IntPtr ptr = Marshal.AllocHGlobal(bytes.Length);
            uint Nsizeptr2 = 10000;
            IntPtr ptr2 = Marshal.AllocHGlobal(10000);

            bool iHandle = CHCNetSDK.NET_DVR_GetDeviceAbility(lUserID, CHCNetSDK.DEVICE_SOFTHARDWARE_ABILITY, ptr, nSize, ptr2, Nsizeptr2);

            if (iHandle == false)
            {
                Console.WriteLine("NET_DVR_GET_WORK_STATUS_V50 failed, error:" + CHCNetSDK.NET_DVR_GetLastError());
                return;
            }
            else
            {
                Console.WriteLine("NET_DVR_GET_WORK_STATUS_V50 succ");
                // 从非托管内存转换回字符串
                string managedString = Marshal.PtrToStringAnsi(ptr2);

                // 打印转换回来的字符串
                Console.WriteLine(managedString);
            }
        }


        public static void GetDeviceSdkLog(int lUserID)
        {
            CHCNetSDK.NET_DVR_FIND_LOG_COND struFindLogcond = new CHCNetSDK.NET_DVR_FIND_LOG_COND ();
            struFindLogcond.dwMainType = 0xff;
            int lLongHandle = CHCNetSDK.NET_DVR_FindDVRLog_V50(lUserID, ref struFindLogcond);
            
            while (true)
            {
                CHCNetSDK.NET_DVR_LOG_V50 struFileInfo = new CHCNetSDK.NET_DVR_LOG_V50();
                int bRet = CHCNetSDK.NET_DVR_FindNextLog_V50(lLongHandle, ref struFileInfo);
     
                if (bRet == CHCNetSDK.NET_DVR_FILE_SUCCESS)
                {
                    if (struFileInfo.strLogTime.cTimeDifferenceH != 0x7F && struFileInfo.strLogTime.cTimeDifferenceM != 0x7F)
                    {
                        Console.WriteLine("Year: {0:D4}", struFileInfo.strLogTime.wYear);
                        Console.WriteLine("Month: {0:D2}", struFileInfo.strLogTime.byMonth);
                        Console.WriteLine("Day: {0:D2}", struFileInfo.strLogTime.byDay);
                    }
                    else
                    {
                        Console.WriteLine("{struFileInfo.wYear:D4}-{struFileInfo.byMonth:D2}-{struFileInfo.byDay:D2} {struFileInfo.byHour:D2}:{struFileInfo.byMinute:D2}:{struFileInfo.bySecond:D2}");
                    }

                    switch (struFileInfo.dwMajorType)
                    {
                        case 1:
                            Console.WriteLine("Alarm");
                            break;
                        case 2:
                            Console.WriteLine("Abnormal");
                            break;
                        case 3:
                            Console.WriteLine("Operation");
                            break;
                        case 4:
                            Console.WriteLine("Additional information");
                            break;
                        default:
                            Console.WriteLine("Unknown");
                            break;
                    }
                    const int MAX_NAMELEN = 16;

                    byte[] sNetUser = new byte[MAX_NAMELEN];
                    byte[] sPanelUser = new byte[MAX_NAMELEN];                    
                  
                    Array.Copy(sNetUser, struFileInfo.sNetUser, sNetUser.Length);                    
                    Array.Copy(sPanelUser, struFileInfo.sPanelUser, sPanelUser.Length);
               
                    string szNetUser = Encoding.ASCII.GetString(struFileInfo.sNetUser).TrimEnd('\0');
                    string szPanelUser = Encoding.ASCII.GetString(struFileInfo.sPanelUser).TrimEnd('\0');
                    string szLan = "[{szNetUser}-{szPanelUser}]";

                    if (struFileInfo.dwChannel > 0)
                    {
                        szLan += "chan[{struFileInfo.dwChannel}]";
                    }

                    if (struFileInfo.dwAlarmInPort != 0)
                    {
                        szLan += "AlarmIn[{struFileInfo.dwAlarmInPort}]";
                    }

                    if (struFileInfo.dwAlarmOutPort != 0)
                    {
                        szLan += "AlarmOut[{struFileInfo.dwAlarmOutPort}]";
                    }                  

                    if (struFileInfo.dwInfoLen > 0)
                    {                        
                        string str22 = System.Text.Encoding.GetEncoding("GBK").GetString(struFileInfo.sInfo).TrimEnd('\0');
                        // 打印转换后的字符串
                        Console.WriteLine(str22);
                    }
                    else
                    {
                        Console.WriteLine("");
                    }
                }
                else
                {
                    if (bRet == CHCNetSDK.NET_DVR_ISFINDING)
                    {
                        Console.WriteLine("日志搜索中......");
                        Thread.Sleep(1000);
                        continue;
                    }
                    if (bRet == CHCNetSDK.NET_DVR_NOMOREFILE || bRet == CHCNetSDK.NET_DVR_FILE_NOFIND)
                    {
                        Console.WriteLine("搜索日志结束!");
                        break;
                    }
                    else
                    {
                        Console.WriteLine("由于服务器忙,或网络故障,搜索日志异常终止!");
                        break;
                    }
                }
            }
            CHCNetSDK.NET_DVR_FindLogClose_V30(lLongHandle);
        }
    }
}
