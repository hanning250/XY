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
    class ACSManage
    {
        public const int IPCHANNEL1 = 1;
        public static bool bStopFlag = false;
        public static void acsCfg(int lUserID)
        {
            CHCNetSDK.NET_DVR_ACS_CFG struAcsCfg = new CHCNetSDK.NET_DVR_ACS_CFG();
            struAcsCfg.dwSize = (uint)Marshal.SizeOf(struAcsCfg);
            IntPtr ptrAcsCfg = Marshal.AllocHGlobal(Marshal.SizeOf(struAcsCfg));
            Marshal.StructureToPtr(struAcsCfg, ptrAcsCfg, false);

            UInt32 intByReference = 0;
            if (!CHCNetSDK.NET_DVR_GetDVRConfig(lUserID, CHCNetSDK.NET_DVR_GET_ACS_CFG, 0xFFFFFF, ptrAcsCfg,
                (uint)Marshal.SizeOf(struAcsCfg), ref intByReference))
            {
                Console.WriteLine("获取门禁主机参数，错误码为" + CHCNetSDK.NET_DVR_GetLastError());
                Marshal.FreeHGlobal(ptrAcsCfg);
                return;
            }
            else
            {
                Console.WriteLine("获取门禁主机参数成功");
                CHCNetSDK.NET_DVR_ACS_CFG retrievedCfg = (CHCNetSDK.NET_DVR_ACS_CFG)Marshal.PtrToStructure(ptrAcsCfg, typeof(CHCNetSDK.NET_DVR_ACS_CFG));
                Marshal.FreeHGlobal(ptrAcsCfg);

                Console.WriteLine("1.是否显示抓拍图片：" + retrievedCfg.byShowCapPic + "\n");  //是否显示抓拍图片， 0-不显示，1-显示
                Console.WriteLine("2.是否显示卡号：" + retrievedCfg.byShowCardNo + "\n");   //是否显示卡号，0-不显示，1-显示
                Console.WriteLine("3.是否开启语音提示：" + retrievedCfg.byVoicePrompt + "\n");  //是否启用语音提示，0-不启用，1-启用
                Console.WriteLine("4.联动抓图是否上传：" + retrievedCfg.byUploadCapPic + "\n"); //联动抓拍是否上传图片，0-不上传，1-上传
            }
            CHCNetSDK.NET_DVR_ACS_CFG setCfg = new CHCNetSDK.NET_DVR_ACS_CFG();
            setCfg.dwSize = (uint)Marshal.SizeOf(setCfg);
            setCfg.byShowCardNo = 1;
            setCfg.byVoicePrompt = 0;
            setCfg.byUploadCapPic = 1;
            setCfg.byShowCapPic = 1;
            IntPtr ptrSetCfg = Marshal.AllocHGlobal(Marshal.SizeOf(setCfg));
            Marshal.StructureToPtr(setCfg, ptrSetCfg, false);
            bool b_SetAcsCfg = CHCNetSDK.NET_DVR_SetDVRConfig(lUserID, CHCNetSDK.NET_DVR_SET_ACS_CFG, 0xFFFFFF, ptrSetCfg, (uint)Marshal.SizeOf(setCfg));
            if (b_SetAcsCfg == false)
            {
                Console.WriteLine("设置门禁主机参数，错误码为：" + CHCNetSDK.NET_DVR_GetLastError());
                Marshal.FreeHGlobal(ptrSetCfg);
                return;
            }
            else
            {
                Console.WriteLine("设置门禁主机参数成功！！！");
                Marshal.FreeHGlobal(ptrSetCfg);
            }
        }


        public static void GetAcsStatus(int lUserID)
        {
            CHCNetSDK.NET_DVR_ACS_WORK_STATUS_V50 netDvrAcsWorkStatusV50 = new CHCNetSDK.NET_DVR_ACS_WORK_STATUS_V50
            {
                byDoorLockStatus = new byte[CHCNetSDK.MAX_DOOR_NUM_256],
                byDoorStatus = new byte[CHCNetSDK.MAX_DOOR_NUM_256],
                byMagneticStatus = new byte[CHCNetSDK.MAX_DOOR_NUM_256],
                byCaseStatus = new byte[CHCNetSDK.MAX_CASE_SENSOR_NUM],
                byCardReaderOnlineStatus = new byte[CHCNetSDK.MAX_CARD_READER_NUM_512],
                byCardReaderAntiDismantleStatus = new byte[CHCNetSDK.MAX_CARD_READER_NUM_512],
                byCardReaderVerifyMode = new byte[CHCNetSDK.MAX_CARD_READER_NUM_512],
                bySetupAlarmStatus = new byte[CHCNetSDK.MAX_ALARMHOST_ALARMIN_NUM],
                byAlarmInStatus = new byte[CHCNetSDK.MAX_ALARMHOST_ALARMIN_NUM],
                byAlarmOutStatus = new byte[CHCNetSDK.MAX_ALARMHOST_ALARMOUT_NUM],
                byRes3 = new byte[3],
                byRes2 = new byte[108]
            };

            netDvrAcsWorkStatusV50.dwSize = (uint)Marshal.SizeOf(netDvrAcsWorkStatusV50);

            IntPtr ptr = Marshal.AllocHGlobal((int)netDvrAcsWorkStatusV50.dwSize);
            try
            {
                Marshal.StructureToPtr(netDvrAcsWorkStatusV50, ptr, false);

                uint lpBytesReturned = 0;
                bool b_GetAcsStatus = CHCNetSDK.NET_DVR_GetDVRConfig(
                    lUserID,
                    CHCNetSDK.NET_DVR_GET_ACS_WORK_STATUS_V50,
                    0xFFFFFF,
                    ptr,
                    netDvrAcsWorkStatusV50.dwSize,
                    ref lpBytesReturned);

                if (!b_GetAcsStatus)
                {
                    Console.WriteLine("获取梯控主机工作状态，错误码为：" + CHCNetSDK.NET_DVR_GetLastError());
                    return;
                }
                else
                {
                    Console.WriteLine("获取梯控主机工作状态成功！！！");
                    netDvrAcsWorkStatusV50 = (CHCNetSDK.NET_DVR_ACS_WORK_STATUS_V50)Marshal.PtrToStructure(ptr, typeof(CHCNetSDK.NET_DVR_ACS_WORK_STATUS_V50));

                    for (int i = 0; i < 128; i++)
                    {
                        int floor = i + 1;
                        Console.WriteLine("楼层" + floor + " 继电器开合状态：" + netDvrAcsWorkStatusV50.byDoorLockStatus[i]);
                        Console.WriteLine("楼层" + floor + " 梯控状态：" + netDvrAcsWorkStatusV50.byDoorStatus[i]);
                    }
                    Console.WriteLine("3.门磁状态：" + netDvrAcsWorkStatusV50.byMagneticStatus[0]);
                    Console.WriteLine("4.事件报警输入状态：" + netDvrAcsWorkStatusV50.byCaseStatus[0]);
                }
            }
            finally
            {
                Marshal.FreeHGlobal(ptr);
            }
        }
    }
}