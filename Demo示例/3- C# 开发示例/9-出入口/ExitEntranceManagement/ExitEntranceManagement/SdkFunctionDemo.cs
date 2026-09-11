using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Runtime.InteropServices;
using ExitEntranceManagement.Common;


namespace ExitEntranceManagement
{
    class SdkFunctionDemo
    {
        private static CHCNetSDK.RemoteConfigCallback m_StateCallback = null;
        private static bool bStopFlag = false;


        public static void addVechileList(int lUserID) 
        {
            if (m_StateCallback == null) {
                m_StateCallback = new CHCNetSDK.RemoteConfigCallback(RemoteConfigCallback);
            }
            int iHandle = CHCNetSDK.NET_DVR_StartRemoteConfig(lUserID, CHCNetSDK.NET_DVR_VEHICLELIST_CTRL_START, IntPtr.Zero, 0, m_StateCallback, IntPtr.Zero);
            if (iHandle < 0)
            {
                Console.WriteLine("NET_DVR_VEHICLELIST_CTRL_START failed, error:" + CHCNetSDK.NET_DVR_GetLastError());
                return;
            }
            else 
            {
                Console.WriteLine("NET_DVR_VEHICLELIST_CTRL_START succ");
            }

            bStopFlag = false;

            CHCNetSDK.NET_DVR_VEHICLE_CONTROL_LIST_INFO m_struVehicleCtrlListInfo = new CHCNetSDK.NET_DVR_VEHICLE_CONTROL_LIST_INFO();
            m_struVehicleCtrlListInfo.Init();

            Int32 dwSize = Marshal.SizeOf(m_struVehicleCtrlListInfo);
            m_struVehicleCtrlListInfo.dwSize = (uint)dwSize;

            m_struVehicleCtrlListInfo.dwChannel = uint.Parse(AppTest.DeviceChannel);    //通道号

            string sLicense = "浙A12345";    //车牌号码
            byte[] byTempLicense = new byte[CHCNetSDK.MAX_LICENSE_LEN];
            byTempLicense = System.Text.Encoding.GetEncoding("GBK").GetBytes(sLicense);
            for (int i = 0; i < byTempLicense.Length; i++)
            {
                m_struVehicleCtrlListInfo.sLicense[i] = byTempLicense[i];
            }   
         
            m_struVehicleCtrlListInfo.byListType = 0; //名单属性：0- 授权名单，1- 非授权名单
            m_struVehicleCtrlListInfo.byPlateType = (byte)CHCNetSDK.VCA_PLATE_TYPE.VCA_STANDARD92_PLATE;//车牌类型
            m_struVehicleCtrlListInfo.byPlateColor = (byte)CHCNetSDK.VCA_PLATE_COLOR.VCA_BLUE_PLATE; //车牌颜色

            //有效开始时间
            m_struVehicleCtrlListInfo.struStartTime.wYear = 2024;
            m_struVehicleCtrlListInfo.struStartTime.byMonth = 1;
            m_struVehicleCtrlListInfo.struStartTime.byDay = 1;
            m_struVehicleCtrlListInfo.struStartTime.byHour = 0;
            m_struVehicleCtrlListInfo.struStartTime.byMinute = 0;
            m_struVehicleCtrlListInfo.struStartTime.bySecond = 0;
            //有效结束时间
            m_struVehicleCtrlListInfo.struStopTime.wYear = 2028;
            m_struVehicleCtrlListInfo.struStopTime.byMonth = 12;
            m_struVehicleCtrlListInfo.struStopTime.byDay = 30;
            m_struVehicleCtrlListInfo.struStopTime.byHour = 23;
            m_struVehicleCtrlListInfo.struStopTime.byMinute = 59;
            m_struVehicleCtrlListInfo.struStopTime.bySecond = 59;

            IntPtr ptrCtrlListInfo = Marshal.AllocHGlobal(dwSize);
            Marshal.StructureToPtr(m_struVehicleCtrlListInfo, ptrCtrlListInfo, false);

            bool bSend = CHCNetSDK.NET_DVR_SendRemoteConfig(iHandle, CHCNetSDK.ENUM_SENDDATA, ptrCtrlListInfo, dwSize);
            if (!bSend)
            {
                Console.WriteLine("NET_DVR_SendRemoteConfig failed, error:" + CHCNetSDK.NET_DVR_GetLastError());
                CHCNetSDK.NET_DVR_StopRemoteConfig(iHandle);    //关闭下发长链接
                return;
            }
            else 
            {
                Console.WriteLine("NET_DVR_SendRemoteConfig succ");
            }
            while (true) 
            {
                if (bStopFlag == true)//根据回调函数状态判断，当下发完成或者出现异常时断开长链接
                {
                    if (!CHCNetSDK.NET_DVR_StopRemoteConfig(iHandle))
                    {
                        Console.WriteLine("NET_DVR_StopRemoteConfig failed, error:" + CHCNetSDK.NET_DVR_GetLastError());
                    }
                    else 
                    {
                        Console.WriteLine("NET_DVR_StopRemoteConfig succ");
                    }
                    break;
                }
            }
        }

        public static void RemoteConfigCallback(uint dwType, IntPtr lpBuffer, uint dwBufLen, IntPtr pUserData)
        {
            if (dwType == (uint)CHCNetSDK.NET_SDK_CALLBACK_TYPE.NET_SDK_CALLBACK_TYPE_STATUS)
            {

                int dwStatus = Marshal.ReadInt32(lpBuffer);
                if (dwStatus == (uint)CHCNetSDK.NET_SDK_CALLBACK_STATUS_NORMAL.NET_SDK_CALLBACK_STATUS_SUCCESS)
                {
                    Console.WriteLine("下发成功");
                    bStopFlag = true;
                }
                else if (dwStatus == (uint)CHCNetSDK.NET_SDK_CALLBACK_STATUS_NORMAL.NET_SDK_CALLBACK_STATUS_PROCESSING)
                {
                    Console.WriteLine("下发中...");
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
                    Console.WriteLine("下发异常");
                    bStopFlag = true;
                }
            }
            return;
        }

        public static void searchVechileList(int lUserID)   //查询车辆授权名单示例代码
        {
            string searchVechileListUrl = "POST /ISAPI/Traffic/channels/1/searchLPListAudit";
            // 输入参数，XML或者JSON数据, 查询多条人员信息json报文
            Dictionary<string, object> parameter = new Dictionary<string, object>();
            parameter.Add("searchID", Guid.NewGuid()); // 查询id
            parameter.Add("maxResults", 30); // 最大查询数量
            string strInbuff = ConfigFileUtil.GetReqBodyFromTemplate("\\conf\\ITC\\searchVechileList.xml", parameter);
            stdXMLConfig(lUserID, searchVechileListUrl, strInbuff);
        }

        public static void deleteVechileList(int lUserID)   //删除车辆授权/非授权名单
        {
            string deleteVechileListUrl = "PUT /ISAPI/Traffic/channels/1/DelLicensePlateAuditData?format=json";
            // 输入参数，XML或者JSON数据, 查询多条人员信息json报文
            Dictionary<string, object> parameter = new Dictionary<string, object>();
            parameter.Add("plateColor", "yellow"); // 车牌颜色
            parameter.Add("licensePlate", "京AA12345"); // 车牌号码
            string strInbuff = ConfigFileUtil.GetReqBodyFromTemplate("\\conf\\ITC\\DeleteVechileList.json", parameter);
            stdXMLConfig(lUserID, deleteVechileListUrl, strInbuff);
        }

        public static void BarrierGateCtrl(int lUserID) //道闸控制示例
        {
            CHCNetSDK.NET_DVR_BARRIERGATE_CFG m_struControlCond = new CHCNetSDK.NET_DVR_BARRIERGATE_CFG();
            Int32 dwSize = Marshal.SizeOf(m_struControlCond);
            m_struControlCond.dwSize = (uint)dwSize;
            m_struControlCond.dwChannel = uint.Parse(AppTest.DeviceChannel);    //通道号
            m_struControlCond.byLaneNo = 1;     //道闸号
            m_struControlCond.byBarrierGateCtrl = 1;    //控制参数：0- 关闭道闸，1- 开启道闸，2- 停止道闸，3- 锁定道闸，4- 解锁道闸 
            m_struControlCond.byEntranceNo = 1;     //出入口编号
            m_struControlCond.byUnlock = 0;     //启用解锁使能

            IntPtr ptrControlCfg = Marshal.AllocHGlobal(dwSize);
            Marshal.StructureToPtr(m_struControlCond, ptrControlCfg, false);

            if (!CHCNetSDK.NET_DVR_RemoteControl(lUserID, CHCNetSDK.NET_DVR_BARRIERGATE_CTRL, ptrControlCfg, dwSize))
            {
                Console.Write("NET_DVR_BARRIERGATE_CTRL failed, error:" + CHCNetSDK.NET_DVR_GetLastError());
            }
            else 
            {
                Console.WriteLine("NET_DVR_BARRIERGATE_CTRL succ");
            }
        }

        public static void getBarrierGateState(int lUserID) //获取道闸状态
        {
            string getBarrierGateStateUrl = "GET /ISAPI/Parking/channels/1/barrierGate/barrierGateStatus";
            stdXMLConfig(lUserID, getBarrierGateStateUrl, "");
        }

        public static void voiceBroadcastInfo(int lUserID)  //平台下发语音播报，适用平台自定义下发文本信息，设备响应进行单独播报
        {
            string voiceBroadcastInfoURL = "PUT /ISAPI/Parking/channels/1/voiceBroadcastInfo";
            Dictionary<string, object> parameter = new Dictionary<string, object>();
            parameter.Add("TTSInfo", "[v1]测试语音播报"); //[V]中数字表示音量等级，取值范围1-10)
            string strInbuff = ConfigFileUtil.GetReqBodyFromTemplate("\\conf\\ITC\\voiceBroadcastInfo.xml", parameter);
            stdXMLConfig(lUserID, voiceBroadcastInfoURL, strInbuff);          
        }

        public static void getCombinateBroadcastInfo(int lUserID)   //获取组合语音播报参数
        {
            string getCombinateBroadcastInfoUrl = "GET /ISAPI/Parking/channels/1/voiceBroadcastInfo/combinateBroadcast?format=json";
            stdXMLConfig(lUserID, getCombinateBroadcastInfoUrl, "");
        }

        public static void setCombinateBroadcastInfo(int lUserID)   //设置组合语音播报参数
        {
            string voiceBroadcastInfoURL = "PUT /ISAPI/Parking/channels/1/voiceBroadcastInfo/combinateBroadcast?format=json";
            string strInbuff = ConfigFileUtil.ReadFileContent("\\conf\\ITC\\CombinateBroadcast.json");
            stdXMLConfig(lUserID, voiceBroadcastInfoURL, strInbuff);                   
        }

         /**
         * 设置相机控制模式LCD字符显示,包含过车和空闲两种场景
         * 相机控制： 相机控制（设备自动控制）：设备自行识别黑、授权名单以及临时车牌，并根据displayPassingVehicleInfoEnabled、allowListDisplayEnabled、blockListDisplayEnabled、temporaryListDisplayEnabled中所配置的策略，自动显示过车信息。
         */
        public static void setCameractrlModeLCDdisplayInfo(int lUserID)
        {
            string CameractrlModeLCDdisplayInfoUrl = "PUT /ISAPI/Parking/channels/1/LCD?format=json&powerOffSaveEnabled=true";
            Dictionary<string, object> parameter = new Dictionary<string, object>();
            parameter.Add("ctrlMode", "camera"); //设置为相机控制模式
            parameter.Add("content", "测试显示内容1"); //设置空闲模式下显示文本内容
            string strInbuff = ConfigFileUtil.GetReqBodyFromTemplate("\\conf\\ITC\\CameractrlModeLCDdisplayInfo.json", parameter);
            stdXMLConfig(lUserID, CameractrlModeLCDdisplayInfoUrl, strInbuff);      
        }

        public static void getctrlModeLCDdisplayInfo(int lUserID)   //获取当前LCD参数示例代码
        {
            string getLCDdisplayInfoUrl = "GET /ISAPI/Parking/channels/1/LCD?format=json";
            stdXMLConfig(lUserID, getLCDdisplayInfoUrl, "");
        }

         /**
         * 设置平台控制模式LCD参数显示
         * 平台控制模式： 平台控制（手动控制）：完全由用户下发CustomContentList内容来显示，该模式displayPassingVehicleInfoEnabled、
         * allowListDisplayEnabled、blockListDisplayEnabled、temporaryListDisplayEnabled中所配置的自动控制策略将不生效。
         * 此接口可以设置平台控制模式下字体大小，颜色等参数，/ISAPI/System/LCDScreen/displayInfo?format=json接口仅负责下发内容参数
         * @param lUserID
         */
        public static void setplatformctrlModeLCDdisplayInfo(int lUserID)
        {
            string platformctrlModeLCDdisplayInfoUrl = "PUT /ISAPI/Parking/channels/1/LCD?format=json&powerOffSaveEnabled=true";
            /**
             * 平台控制模式下LCD显示效果，可以调用POST /ISAPI/System/LCDScreen/displayInfo?format=json接口根据场景自定义下发内容
             */
            Dictionary<string, object> parameter = new Dictionary<string, object>();
            parameter.Add("ctrlMode", "platform"); //设置为相机控制模式
            parameter.Add("content", "测试显示内容1"); //设置空闲模式下显示文本内容
            string strInbuff = ConfigFileUtil.GetReqBodyFromTemplate("\\conf\\ITC\\CameractrlModeLCDdisplayInfo.json", parameter);
            stdXMLConfig(lUserID, platformctrlModeLCDdisplayInfoUrl, strInbuff);
        }

         /**
         * 设置LCD图片显示，一般用于二维码图片显示，通常适用2-入场无车牌、4-出场有车牌未付费、5-出场无车牌三种场景
         * @param lUserID
         */
        public static void setPicDisplayEnterNolicense(int lUserID)
        {
            string setPicDisplayUrl = "POST /ISAPI/System/LCDScreen/displayInfo?format=json";

            Dictionary<string, object> parameter = new Dictionary<string, object>();
            parameter.Add("QRCodeBase64", "iVBORw0KGgoAAAANSUhEUgAAAPoAAAD6CAIAAAAHjs1qAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAEKElEQVR4nO3dwW7bMBQAwb" +
                 "rw//9yeumZCsKyJL0z1yC2oix4eXjS69fH+fr6WvTJr9fruu9d97s3+r37AuD/kTshcidE7oTInRC5EyJ3QuROiNwJeY9/vG5SOGPdtG/d3HTXhHLdf/DGN" +
                 "pzuhMidELkTIndC5E6I3AmROyFyJ0TuhDxMVcfWTQpv3Pscu3EiO+PMNpzuhMidELkTIndC5E6I3AmROyFyJ0TuhExNVT/PupnrzCefOeu9kdOdELkTIndC5" +
                 "E6I3AmROyFyJ0TuhMidEFPVf2bd7PPGXdUzOd0JkTshcidE7oTInRC5EyJ3QuROiNwJmZqq1jYdz9w3PdOZbTjdCZE7IXInRO6EyJ0QuRMid0LkTojcCXmYqn" +
                 "7etG9s177pzPfumtfe2IbTnRC5EyJ3QuROiNwJkTshcidE7oTInZD3mTuFu6ybFN54n2+85jGnOyFyJ0TuhMidELkTIndC5E6I3AmROyEPQ8Qbn1s7Mws8c6N" +
                 "03e+Ofd7/1+lOiNwJkTshcidE7oTInRC5EyJ3QuROyMKx2Zmbjru2UW+cfa6bqa9rY3xVTndC5E6I3AmROyFyJ0TuhMidELkTIndCpnZVHz76wjnijF17vbvu5" +
                 "I3bt053QuROiNwJkTshcidE7oTInRC5EyJ3Ql5nbljeOHPddSfHztwo3cXpTojcCZE7IXInRO6EyJ0QuRMid0LkTsi2XdV1Pu+5tbu2QndZd81Od0LkTojcCZE" +
                 "7IXInRO6EyJ0QuRMid0Kmpqo3Pj92rDY3vfGpxTOc7oTInRC5EyJ3QuROiNwJkTshcidE7oS8d1/AT+x6mu6MM+eXu+biY+vuhtOdELkTIndC5E6I3AmROyFyJ" +
                 "0TuhMidkIW7qrWN0plPHjtzTryLJwDDt8idELkTIndC5E6I3AmROyFyJ0TuhCx8r+rDF8feunrmG0zPtG567XQnRO6EyJ0QuRMid0LkTojcCZE7IXIn5FXbg7zx6" +
                 "cE3vt901302VYW/5E6I3AmROyFyJ0TuhMidELkTIndC3p+3Qzme2O16iu+NzpyMznC6EyJ3QuROiNwJkTshcidE7oTInRC5E/Ie//jzdjd3TQp33ckz3+e667/gd" +
                 "CdE7oTInRC5EyJ3QuROiNwJkTshcifkYao6duOTacfW/UUzc8R1M8ja9q3TnRC5EyJ3QuROiNwJkTshcidE7oTInZCpqWrNrvnlzMx1xrq/d9eddLoTIndC5E6I3A" +
                 "mROyFyJ0TuhMidELkTYqp6hF3P6T1zV3XdXq/TnRC5EyJ3QuROiNwJkTshcidE7oTInZCHodqN71V1zd//3jOtex6y050QuRMid0LkTojcCZE7IXInRO6EyJ2Q+0Z" +
                 "uj3a9o3SdM9/Jus66SbDTnRC5EyJ3QuROiNwJkTshcidE7oTInZA/2q1JFatAjGUAAAAASUVORK5CYII="); //图片BASE64编码
            parameter.Add("sence", "2"); //设置场景模式，2-入场无车牌
            parameter.Add("license", "无车牌"); //车牌内容
            parameter.Add("amounts", "0"); //金额随意下发，此场景不显示
            parameter.Add("notice", "无牌车请扫码"); //通知信息
            string strInbuff = ConfigFileUtil.GetReqBodyFromTemplate("\\conf\\ITC\\PicDisPlayInfo.json", parameter);
            stdXMLConfig(lUserID, setPicDisplayUrl, strInbuff);
        }

         /**
         * 设置LCD图片显示，一般用于二维码图片显示，通常适用2-入场无车牌、4-出场有车牌未付费、5-出场无车牌三种场景
         * @param lUserID
         */
        public static void setPicDisplayExitNoPay(int lUserID)
        {
            string setPicDisplayUrl = "POST /ISAPI/System/LCDScreen/displayInfo?format=json";

            Dictionary<string, object> parameter = new Dictionary<string, object>();
            parameter.Add("QRCodeBase64", "iVBORw0KGgoAAAANSUhEUgAAAPoAAAD6CAIAAAAHjs1qAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAEKElEQVR4nO3dwW7bMBQAwb" +
                 "rw//9yeumZCsKyJL0z1yC2oix4eXjS69fH+fr6WvTJr9fruu9d97s3+r37AuD/kTshcidE7oTInRC5EyJ3QuROiNwJeY9/vG5SOGPdtG/d3HTXhHLdf/DGN" +
                 "pzuhMidELkTIndC5E6I3AmROyFyJ0TuhDxMVcfWTQpv3Pscu3EiO+PMNpzuhMidELkTIndC5E6I3AmROyFyJ0TuhExNVT/PupnrzCefOeu9kdOdELkTIndC5" +
                 "E6I3AmROyFyJ0TuhMidEFPVf2bd7PPGXdUzOd0JkTshcidE7oTInRC5EyJ3QuROiNwJmZqq1jYdz9w3PdOZbTjdCZE7IXInRO6EyJ0QuRMid0LkTojcCXmYqn" +
                 "7etG9s177pzPfumtfe2IbTnRC5EyJ3QuROiNwJkTshcidE7oTInZD3mTuFu6ybFN54n2+85jGnOyFyJ0TuhMidELkTIndC5E6I3AmROyEPQ8Qbn1s7Mws8c6N" +
                 "03e+Ofd7/1+lOiNwJkTshcidE7oTInRC5EyJ3QuROyMKx2Zmbjru2UW+cfa6bqa9rY3xVTndC5E6I3AmROyFyJ0TuhMidELkTIndCpnZVHz76wjnijF17vbvu5" +
                 "I3bt053QuROiNwJkTshcidE7oTInRC5EyJ3Ql5nbljeOHPddSfHztwo3cXpTojcCZE7IXInRO6EyJ0QuRMid0LkTsi2XdV1Pu+5tbu2QndZd81Od0LkTojcCZE" +
                 "7IXInRO6EyJ0QuRMid0Kmpqo3Pj92rDY3vfGpxTOc7oTInRC5EyJ3QuROiNwJkTshcidE7oS8d1/AT+x6mu6MM+eXu+biY+vuhtOdELkTIndC5E6I3AmROyFyJ" +
                 "0TuhMidkIW7qrWN0plPHjtzTryLJwDDt8idELkTIndC5E6I3AmROyFyJ0TuhCx8r+rDF8feunrmG0zPtG567XQnRO6EyJ0QuRMid0LkTojcCZE7IXIn5FXbg7zx6" +
                 "cE3vt901302VYW/5E6I3AmROyFyJ0TuhMidELkTIndC3p+3Qzme2O16iu+NzpyMznC6EyJ3QuROiNwJkTshcidE7oTInRC5E/Ie//jzdjd3TQp33ckz3+e667/gd" +
                 "CdE7oTInRC5EyJ3QuROiNwJkTshcifkYao6duOTacfW/UUzc8R1M8ja9q3TnRC5EyJ3QuROiNwJkTshcidE7oTInZCpqWrNrvnlzMx1xrq/d9eddLoTIndC5E6I3A" +
                 "mROyFyJ0TuhMidELkTYqp6hF3P6T1zV3XdXq/TnRC5EyJ3QuROiNwJkTshcidE7oTInZCHodqN71V1zd//3jOtex6y050QuRMid0LkTojcCZE7IXInRO6EyJ2Q+0Z" +
                 "uj3a9o3SdM9/Jus66SbDTnRC5EyJ3QuROiNwJkTshcidE7oTInZA/2q1JFatAjGUAAAAASUVORK5CYII="); //图片BASE64编码
            parameter.Add("sence", "4"); //设置场景模式，4-出场有车牌未付费
            parameter.Add("license", "浙A12345"); //车牌内容
            parameter.Add("amounts", "30"); //缴费金额
            parameter.Add("notice", "请缴费"); //通知信息
            string strInbuff = ConfigFileUtil.GetReqBodyFromTemplate("\\conf\\ITC\\PicDisPlayInfo.json", parameter);
            stdXMLConfig(lUserID, setPicDisplayUrl, strInbuff);
        }

         /**
         * 平台模式下，车辆入场有车牌场景自定义下发显示
         * @param lUserID
         */
        public static void setEnterLicenseDisplay(int lUserID)
        {
            string setPicDisplayUrl = "POST /ISAPI/System/LCDScreen/displayInfo?format=json";

            Dictionary<string, object> parameter = new Dictionary<string, object>();
            parameter.Add("sence", "1"); //设置场景模式，1-入场有车牌
            parameter.Add("license", "浙A12345"); //车牌内容
            parameter.Add("enterTime", "2024-08-03 17:30:00"); //入场时间
            parameter.Add("customInfo", "入场有车牌"); //通知信息
            string strInbuff = ConfigFileUtil.GetReqBodyFromTemplate("\\conf\\ITC\\EnterLiceseDisplay.json", parameter);
            stdXMLConfig(lUserID, setPicDisplayUrl, strInbuff);
        }

         /**
         * 空闲场景下余位显示，余位显示需要先设备端开启余位显示，可以在设备web页面入口设置中开启，也可以通过PUT /ISAPI/Parking/channels/1/LCD?format=json&powerOffSaveEnabled=true接口开启余位显示
         * @param lUserID
         */
        public static void setParkingLotDisPlay(int lUserID)
        {
            string setPicDisplayUrl = "POST /ISAPI/System/LCDScreen/displayInfo?format=json";

            Dictionary<string, object> parameter = new Dictionary<string, object>();
            parameter.Add("sence", "10"); //设置场景模式，10-空闲场景
            parameter.Add("parkingLot", "100"); //余位信息
            string strInbuff = ConfigFileUtil.GetReqBodyFromTemplate("\\conf\\ITC\\ParkingLotDisPlay.json", parameter);
            stdXMLConfig(lUserID, setPicDisplayUrl, strInbuff);
        }

        /** 获取LED屏幕单场景显示参数(需要看设备是否支持此功能，例如守尉设备支持)
        * 命令：GET /ISAPI/Parking/channels/<channelID>/LEDConfigurations/multiScene/<SID>?format=json
        * channelID =通道号，一般默认1
        * SID场景号：1：passingVehicle（过车场景），2：noVehicle（无过车场景）
        * */
        public static void getLEDdisplayMultiScene(int lUserID)   
        {
            string getLEDdisplayInfoUrl = "GET /ISAPI/Parking/channels/1/LEDConfigurations/multiScene/1?format=json";
            stdXMLConfig(lUserID, getLEDdisplayInfoUrl, "");
        }

         /**
         * 设置LED屏幕单场景显示参数(需要看设备是否支持此功能，例如守尉设备支持)
         * @param lUserID
         */
        public static void setLEDdisplayMultiScene(int lUserID)
        {
            string setLEDdisplayMultiSceneUrl = "PUT /ISAPI/Parking/channels/1/LEDConfigurations/multiScene/2?format=json";
            //空闲场景输入报文
            string strInbuff = ConfigFileUtil.ReadFileContent("\\conf\\ITC\\SingleSceneLEDConfigurations.json");
            stdXMLConfig(lUserID, setLEDdisplayMultiSceneUrl, strInbuff);            
        }

        public static void stdXMLConfig(int lUserID, string url, string inputStr)//该函数封装了SDK透传接口NET_DVR_STDXMLConfig
        {
            CHCNetSDK.NET_DVR_XML_CONFIG_INPUT pInputXml = new CHCNetSDK.NET_DVR_XML_CONFIG_INPUT();
            Int32 nInSize = Marshal.SizeOf(pInputXml);
            pInputXml.dwSize = (uint)nInSize;

            //输入ISAPI协议命令
            uint dwRequestUrlLen = (uint)url.Length;
            pInputXml.lpRequestUrl = Marshal.StringToHGlobalAnsi(url);
            pInputXml.dwRequestUrlLen = dwRequestUrlLen;
            Console.WriteLine("透传URL:" + url);

            //输入XML/JSON报文, GET命令输入报文为空
            if (inputStr != "") 
            {
                byte[] byInputParam = Encoding.UTF8.GetBytes(inputStr);
                int iXMLInputLen = byInputParam.Length;

                pInputXml.lpInBuffer = Marshal.AllocHGlobal(iXMLInputLen);
                Marshal.Copy(byInputParam, 0, pInputXml.lpInBuffer, iXMLInputLen);
                pInputXml.dwInBufferSize = (uint)byInputParam.Length;

                Console.WriteLine("透传输入报文:" + inputStr);
            }

            CHCNetSDK.NET_DVR_XML_CONFIG_OUTPUT pOutputXml = new CHCNetSDK.NET_DVR_XML_CONFIG_OUTPUT();
            pOutputXml.dwSize = (uint)Marshal.SizeOf(pInputXml);
            pOutputXml.lpOutBuffer = Marshal.AllocHGlobal(8 * 1024);    //输出缓冲区，如果接口调用失败提示错误码43，需要增大输出缓冲区
            pOutputXml.dwOutBufferSize = 8 * 1024;
            pOutputXml.lpStatusBuffer = Marshal.AllocHGlobal(1024);
            pOutputXml.dwStatusSize = 1024;

            if (!CHCNetSDK.NET_DVR_STDXMLConfig(lUserID, ref pInputXml, ref pOutputXml))
            {
                Console.WriteLine("NET_DVR_STDXMLConfig failed, error:" + CHCNetSDK.NET_DVR_GetLastError());
                return;
            }

            uint iXMSize = pOutputXml.dwReturnedXMLSize;
            byte[] managedArray = new byte[iXMSize];
            Marshal.Copy(pOutputXml.lpOutBuffer, managedArray, 0, (int)iXMSize);
            string strOutBuffer = Encoding.UTF8.GetString(managedArray);
            string strStatusBuffer = Marshal.PtrToStringAnsi(pOutputXml.lpStatusBuffer);
            Console.WriteLine("NET_DVR_STDXMLConfig succ");
            if (strOutBuffer != "") 
            {
                Console.WriteLine("strOutBuffer:" + strOutBuffer);            
            }
            if (strStatusBuffer != "")
            {
                Console.WriteLine("strStatusBuffer:" + strStatusBuffer);
            }
            Marshal.FreeHGlobal(pInputXml.lpRequestUrl);
            Marshal.FreeHGlobal(pOutputXml.lpOutBuffer);
            Marshal.FreeHGlobal(pOutputXml.lpStatusBuffer);

        }


    }
}
