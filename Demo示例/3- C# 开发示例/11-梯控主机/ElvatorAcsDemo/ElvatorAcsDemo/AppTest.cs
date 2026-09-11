using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using ElvatorAcsDemo.Common;

namespace ElvatorAcsDemo
{
    class AppTest
    {
        static string sCurPath = AppDomain.CurrentDomain.BaseDirectory;        
        static int m_lUserID = -1;    //登录句柄
        static string DeviceIP = "10.10.138.12";  //读取设备IP
        static string DevicePort ="8000";  //读取设备服务端口
        static string DeviceUser ="admin";  //读取设备用户名
        static string DevicePassWord = "Cpfwb518+";  //读取设备密码
        public static string DeviceChannel ="1";    //读取设备通道号
        public static int iCharEncodeType = 0;

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
                iCharEncodeType = DeviceInfo.byCharEncodeType;
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
                            Console.WriteLine("[Module获取梯控主机参数示例代码");
                            ACSManage.acsCfg(m_lUserID);
                            break;
                        }
                    case "2":
                        {
                            Console.WriteLine("[Module获取梯控主机状态示例代码");
                            ACSManage.GetAcsStatus(m_lUserID);
                            break;
                        }
                    case "3":
                        {
                            Console.WriteLine("[Module远程梯控示例代码");
                            DoorManage.controlGateway(m_lUserID, 1, 0);
                            break;
                        }
                    case "4":
                        {
                            Console.WriteLine("[Module下发卡号示例代码");
                            CardManage.SetOneCard(m_lUserID, "123", 1);
                            break;
                        }
                    case "5":
                        {
                            Console.WriteLine("[Module查询卡号示例代码");
                            CardManage.GetOneCard(m_lUserID, "123");
                            break;
                        }
                    case "6":
                        {
                            Console.WriteLine("[Module查询所有卡号示例代码");
                            CardManage.GetAllCards(m_lUserID);
                            break;
                        }
                    case "7":
                        {
                            Console.WriteLine("[Module删除卡号代码");
                            CardManage.DeleteOneCard(m_lUserID, "123");
                            break;
                        }
                    case "8":
                        {
                            Console.WriteLine("[Module删除所有卡号代码");
                            CardManage.CleanCardInfo(m_lUserID);
                            break;
                        }                        
                    case "9":
                        {
                            Console.WriteLine("[Module设置卡计划模板代码");
                            CardManage.SetCardTemplate(m_lUserID, 2);
                            break;
                        }                    
                    case "10":
                        {
                            Console.WriteLine("[Module获取与设置楼层参数");
                            DoorManage.GetAndSetFloorCfg(m_lUserID, 1);
                            break;
                        }
                    case "11":
                        {
                            Console.WriteLine("[Module门禁历史事件查询代码");
                            EventSearch.SearchAllEvent(m_lUserID);
                            break;
                        }
                    case "12":
                        {
                            Console.WriteLine("[Module设置梯控计划模板代码");
                            DoorManage.ConfigureElevatorTemplate(m_lUserID, 1, 1);
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
