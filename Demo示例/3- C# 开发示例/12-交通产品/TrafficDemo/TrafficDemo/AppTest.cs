using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using TrafficDemo.Common;

namespace TrafficDemo
{
    class AppTest
    {
        static string sCurPath = AppDomain.CurrentDomain.BaseDirectory;
        static string configPath = sCurPath + "/config.properties";     //获取配置文件所在路径，从配置文件中读取设备IP、端口、用户名和密码以及通道号等信息
        static int m_lUserID = -1;    //登录句柄

        static string DeviceIP = CommonMethod.ReadConfigValue(configPath, "DeviceIP");  //从配置文件读取设备IP
        static string DevicePort = CommonMethod.ReadConfigValue(configPath, "DevicePort");  //从配置文件读取设备服务端口
        static string DeviceUser = CommonMethod.ReadConfigValue(configPath, "DeviceUser");  //从配置文件读取设备用户名
        static string DevicePassWord = CommonMethod.ReadConfigValue(configPath, "DevicePassWord");  //从配置文件读取设备密码
        public static string DeviceChannel = CommonMethod.ReadConfigValue(configPath, "DeviceChannel");    //从配置文件读取设备通道号

        static void Main(string[] args)
        {
            CHCNetSDK.NET_DVR_Init();
            CHCNetSDK.NET_DVR_SetLogToFile(3, sCurPath + "/SdkLog", false); //日志的等级（默认为0）：0-表示关闭日志，1-表示只输出ERROR错误日志，2-输出ERROR错误信息和DEBUG调试信息，3-输出ERROR错误信息、DEBUG调试信息和INFO普通信息等所有信息
            
            //设备IP地址或者域名
            CHCNetSDK.NET_DVR_USER_LOGIN_INFO struLogInfo = new CHCNetSDK.NET_DVR_USER_LOGIN_INFO();
            byte[] byIP = System.Text.Encoding.Default.GetBytes(DeviceIP);
            struLogInfo.sDeviceAddress = new byte[129];
            byIP.CopyTo(struLogInfo.sDeviceAddress, 0);

            //设备用户名
            byte[] byUserName = System.Text.Encoding.Default.GetBytes(DeviceUser);
            struLogInfo.sUserName = new byte[64];
            byUserName.CopyTo(struLogInfo.sUserName, 0);

            //设备密码
            byte[] byPassword = System.Text.Encoding.Default.GetBytes(DevicePassWord);
            struLogInfo.sPassword = new byte[64];
            byPassword.CopyTo(struLogInfo.sPassword, 0);

            struLogInfo.wPort = ushort.Parse(DevicePort);//设备服务端口号

            CHCNetSDK.NET_DVR_DEVICEINFO_V40 DeviceInfo = new CHCNetSDK.NET_DVR_DEVICEINFO_V40();
            //登录设备 Login the device
            m_lUserID = CHCNetSDK.NET_DVR_Login_V40(ref struLogInfo, ref DeviceInfo);
            if (m_lUserID < 0)
            {
                Console.Write("NET_DVR_Login_V40 failed, error:" + CHCNetSDK.NET_DVR_GetLastError());
                return;
            }
            else 
            {
                Console.WriteLine("NET_DVR_Login_V40 succ, sSerialNumber:" + Encoding.Default.GetString(DeviceInfo.struDeviceV30.sSerialNumber));
            }


            bool exit = false;
            while (!exit)
            {
                Console.WriteLine("请输入您想要执行的demo实例! （退出请输入yes）");
                string str = Console.ReadLine(); // 从控制台读取一行文本

                // 转换为小写
                str = str.ToLower();
                if (str == "yes")
                {
                    // 退出循环
                    exit = true;
                    break;
                }

                switch (str.ToLower())
                {
                    case "1":
                    {
                        Console.WriteLine("[Module]网络触发抓拍示例代码");
                        SdkFunctionDemo.continuousShoot(m_lUserID);
                        break;
                    }
                    case "2":
                    {
                        Console.WriteLine("[Module]手动触发抓拍示例代码");
                        SdkFunctionDemo.manualSnap(m_lUserID);
                        break;
                    }
                    case "3":
                    {
                        Console.WriteLine("[Module]获取雷视目标数据示例代码");
                        SdkFunctionDemo.getAlarmInfo(m_lUserID);
                        break;
                    }
                    case "4":
                    {
                        Console.WriteLine("[Module]交通数据获取示例代码");
                        SdkFunctionDemo.searchTrafficData(m_lUserID);
                        break;
                    }
                    default: 
                    {
                        Console.WriteLine("未知的指令操作!请重新输入!");
                        break;                    
                    }
                }
            }            
        }
    }
}
