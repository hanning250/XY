using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Runtime.InteropServices;
using TrafficDemo.Common;
using System.Xml;
using System.Xml.XPath;
using System.IO;
using System.Threading;

namespace TrafficDemo
{
    class SdkFunctionDemo
    {
        private static CHCNetSDK.RemoteConfigCallback m_StateCallback = null;

        public static void continuousShoot(int lUserID)
        {
            CHCNetSDK.NET_DVR_SNAPCFG struSnapCfg = new CHCNetSDK.NET_DVR_SNAPCFG();
            struSnapCfg.Init();
            struSnapCfg.dwSize = (uint)Marshal.SizeOf(struSnapCfg);
            struSnapCfg.byRelatedDriveWay = 1;  //关联车道号
            struSnapCfg.bySnapTimes = 1;    //连拍次数
            struSnapCfg.wSnapWaitTime = 100;    //等待100ms
            struSnapCfg.wIntervalTime[0] = 100; //连拍间隔时间
            struSnapCfg.dwSnapVehicleNum = 1;   //抓拍车辆序号

            if (!CHCNetSDK.NET_DVR_ContinuousShoot(lUserID, ref struSnapCfg))
            {
                Console.WriteLine("NET_DVR_ContinuousShoot failed, error:" + CHCNetSDK.NET_DVR_GetLastError());
                return;
            }
            else
            {
                Console.WriteLine("NET_DVR_ContinuousShoot succ");
            }
        }

        public static void manualSnap(int lUserID)
        {
            CHCNetSDK.NET_DVR_PLATE_RESULT struPlateResultInfo = new CHCNetSDK.NET_DVR_PLATE_RESULT();

            CHCNetSDK.NET_DVR_MANUALSNAP struInter = new CHCNetSDK.NET_DVR_MANUALSNAP();
            struInter.byLaneNo = 1; //车道号
            struInter.byChannel = 1;//通道号

            if (!CHCNetSDK.NET_DVR_ManualSnap(lUserID, ref struInter, ref struPlateResultInfo))
            {
                Console.WriteLine("NET_DVR_ManualSnap failed, error:" + CHCNetSDK.NET_DVR_GetLastError());
                return;
            }
            else
            {
                Console.WriteLine("NET_DVR_ManualSnap succ, 车牌号:" + Encoding.GetEncoding("GBK").GetString(struPlateResultInfo.struPlateInfo.sLicense).TrimEnd('\0'));
            }
        }

        private static FileStream fs = null;
        private static BinaryWriter bw = null;
        private static string FileName = "";

        public static void RemoteConfigCallback(uint dwType, IntPtr lpBuffer, uint dwBufLen, IntPtr pUserData)
        {
            // 记录进入回调的时间
            DateTime enterTime = DateTime.Now;
            long startTicks = Environment.TickCount;
            try
            {
                switch (dwType)
                {
                    case (uint)CHCNetSDK.NET_SDK_CALLBACK_TYPE.NET_SDK_CALLBACK_TYPE_STATUS:
                        {
                            int dwStatus = Marshal.ReadInt32(lpBuffer);
                            if (dwStatus == (uint)CHCNetSDK.NET_SDK_CALLBACK_STATUS_NORMAL.NET_SDK_CALLBACK_STATUS_SUCCESS)
                            {
                                Console.WriteLine("NET_SDK_CALLBACK_STATUS_SUCCESS");
                            }
                            else if (dwStatus == (uint)CHCNetSDK.NET_SDK_CALLBACK_STATUS_NORMAL.NET_SDK_CALLBACK_STATUS_PROCESSING)
                            {
                                Console.WriteLine("NET_SDK_CALLBACK_STATUS_PROCESSING");
                            }
                            else if (dwStatus == (uint)CHCNetSDK.NET_SDK_CALLBACK_STATUS_NORMAL.NET_SDK_CALLBACK_STATUS_FAILED)
                            {

                                int InitpBuffer = 4;
                                int pBufferTemp = 0;

                                pBufferTemp = Marshal.ReadInt32(lpBuffer, InitpBuffer);
                                if (pBufferTemp != 0)
                                {
                                    Console.WriteLine("NET_SDK_CALLBACK_STATUS_FAILED,错误码： dwStatus:" + pBufferTemp);
                                }
                            }
                            else if (dwStatus == (uint)CHCNetSDK.NET_SDK_CALLBACK_STATUS_NORMAL.NET_SDK_CALLBACK_STATUS_EXCEPTION)
                            {
                                Console.WriteLine("NET_SDK_CALLBACK_STATUS_EXCEPTION");
                            }
                            break;
                        }
                    case (uint)CHCNetSDK.NET_SDK_CALLBACK_TYPE.NET_SDK_CALLBACK_TYPE_DATA:
                        {
                            // CHCNetSDK.NET_DVR_ALARM_SEARCH_RESULT struRadarResult = new CHCNetSDK.NET_DVR_ALARM_SEARCH_RESULT();
                            //  struRadarResult = (CHCNetSDK.NET_DVR_ALARM_SEARCH_RESULT)Marshal.PtrToStructure(lpBuffer, typeof(CHCNetSDK.NET_DVR_ALARM_SEARCH_RESULT));
                            //       Console.WriteLine("[" + DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss.fff") + "] 查询到雷视目标信息, dwAlarmComm:0x" + struRadarResult.dwAlarmComm.ToString("x")
                            //+ ",报警设备序列号:" + System.Text.Encoding.UTF8.GetString(struRadarResult.struAlarmer.sSerialNumber).TrimEnd('\0')
                            //+ ",报警设备IP地址:" + System.Text.Encoding.UTF8.GetString(struRadarResult.struAlarmer.sDeviceIP).TrimEnd('\0'));


                            Console.WriteLine("[" + DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss.fff"));


                            //if (struRadarResult.dwAlarmComm == 0x4993)
                            //{
                            //    FileName = CommonMethod.SaveFilePath("0x4993", ".json", "0x4993");
                            //    try
                            //    {
                            //        fs = new FileStream(FileName, FileMode.Append);
                            //        bw = new BinaryWriter(fs);
                            //        byte[] byteBuf = new byte[struRadarResult.dwAlarmLen];
                            //        Marshal.Copy(struRadarResult.pAlarmInfo, byteBuf, 0, struRadarResult.dwAlarmLen);
                            //        bw.Write(byteBuf);
                            //        bw.Flush();
                            //    }
                            //    catch (System.Exception ex)
                            //    {
                            //        Console.WriteLine(ex.ToString());
                            //    }
                            //    finally
                            //    {
                            //        bw.Close();
                            //        fs.Close();
                            //    }  
                            //}
                            //else if (struRadarResult.dwAlarmComm == 0x6009)
                            //{
                            //    CHCNetSDK.NET_DVR_ALARM_ISAPI_INFO struISAPIAlarm = new CHCNetSDK.NET_DVR_ALARM_ISAPI_INFO();
                            //    struISAPIAlarm = (CHCNetSDK.NET_DVR_ALARM_ISAPI_INFO)Marshal.PtrToStructure(struRadarResult.pAlarmInfo, typeof(CHCNetSDK.NET_DVR_ALARM_ISAPI_INFO));

                            //    FileName = CommonMethod.SaveFilePath("0x6009", ".json", "0x6009");
                            //    try
                            //    {
                            //        fs = new FileStream(FileName, FileMode.Append);
                            //        bw = new BinaryWriter(fs);
                            //        byte[] byteBuf = new byte[struISAPIAlarm.dwAlarmDataLen];
                            //        Marshal.Copy(struISAPIAlarm.pAlarmData, byteBuf, 0, struISAPIAlarm.dwAlarmDataLen);
                            //        bw.Write(byteBuf);
                            //        bw.Flush();
                            //    }
                            //    catch (System.Exception ex)
                            //    {
                            //        Console.WriteLine(ex.ToString());
                            //    }
                            //    finally
                            //    {
                            //        bw.Close();
                            //        fs.Close();
                            //    } 
                            //}
                            break;
                        }
                }



            }
             finally
    {
        // 计算耗时并打印
        long endTicks = Environment.TickCount;
        long elapsedMs = endTicks - startTicks;
        DateTime exitTime = DateTime.Now;       
        Console.WriteLine("耗时:"+elapsedMs+"ms");
    }

            return;
        }

        public static void getAlarmInfo(int lUserID)
        {
            //获取获取设备工作状态
            CHCNetSDK.NET_DVR_ALARM_SEARCH_COND struAlarmSearchCond = new CHCNetSDK.NET_DVR_ALARM_SEARCH_COND();
            int nSize = Marshal.SizeOf(struAlarmSearchCond);
            struAlarmSearchCond.dwSize = Marshal.SizeOf(struAlarmSearchCond);
            struAlarmSearchCond.dwAlarmComm = 0x4993;//0x4993-智能检测报警(雷视目标检测报警)，0x1112-人脸识别结果，0x2902-人脸比对结果
            struAlarmSearchCond.wEventType = 2;//0-表示所有事件,1-混合目标检测（mixedTargetDetection）,2-雷视目标检测（radarVideoDetection）
            struAlarmSearchCond.byNoBoundary = 0;//是否不带boundary，0-否，1-是，仅dwAlarmComm为智能检测报警时有效
            
            IntPtr ptrSearchCond= Marshal.AllocHGlobal(nSize);
            Marshal.StructureToPtr(struAlarmSearchCond, ptrSearchCond, false);
            // 调用NET_DVR_GetDVRConfig获取设备配置
            //设置回调函数 
            if (m_StateCallback == null)
            {
                m_StateCallback = new CHCNetSDK.RemoteConfigCallback(RemoteConfigCallback);
            }
            int iHandle = CHCNetSDK.NET_DVR_StartRemoteConfig(lUserID, CHCNetSDK.NET_DVR_GET_ALARM_INFO, ptrSearchCond, nSize, m_StateCallback, IntPtr.Zero);
            if (iHandle < 0)
            {
                Console.WriteLine("NET_DVR_GET_ALARM_INFO failed, error:" + CHCNetSDK.NET_DVR_GetLastError());
                return;
            }
            else
            {
                Console.WriteLine("NET_DVR_GET_ALARM_INFO succ");
            }


            //Thread.Sleep(5 * 1000);    //Demo功能演示，获取5秒数据

            while (true)
            {
                // 这里可以执行你的周期性任务
                //Console.WriteLine("进程运行中...");
                Thread.Sleep(1000); // 延时1秒，避免CPU占用过高
            }


            if (!CHCNetSDK.NET_DVR_StopRemoteConfig(iHandle))
            {
                Console.WriteLine("NET_DVR_StopRemoteConfig failed, error:" + CHCNetSDK.NET_DVR_GetLastError());
                return;
            }
            else
            {
                Console.WriteLine("NET_DVR_StopRemoteConfig succ");
            }
        }

        public static void searchTrafficData(int lUserID)
        {
            string searchDataUrl = "POST /ISAPI/Traffic/ContentMgmt/dataOperation";

            Dictionary<string, object> parameter = new Dictionary<string, object>();
            // 一级字段
            parameter.Add("operationType", "search");       //<!--req, enum, 操作类型, subType:string, [search#查询,deleteByID#根据ID删除,deleteByTime#根据时间删除], attr:opt{req, string, 取值范围}-->
            parameter.Add("searchID", "CB3CA997-3A30-0001-64F9-5374CEBE1AA3");      //<!--req, string, 本次查询标识-->
            parameter.Add("startTime", "2025-06-12T00:00:00Z");     //<!--req, datetime, 开始时间-->
            parameter.Add("endTime", "2025-06-12T23:59:59Z");       //<!--req, datetime, 结束时间-->
            parameter.Add("dataType", "0");     //<!--req, enum, 数据类型, subType:int, [0#卡口,1#电警,2#事件,3#取证,4#激光特征,5#非授权名单报警数据,6#人体属性,7#人脸属性（人脸抓拍）,8#渣土车,9#路面状态数据,10#能见度数据,11#气象状态数据,12#船舶航道或者航向角偏移检测,13#船舶卡口检测(Ship),14#道路异物检测(foreignObjectInRoadDetection),15#安全帽检测,16#升降梯超员检测,17#道闸开关闸数据,18#CID事件,19#雷达周界,20#火车,21#桥梁挠度异常事件(BridgeDeflectionAbnormalEvent),22#人脸比对(alarmResult),23#车辆OBU标签信息上报(vehicleOBUInfo),24#智慧城管(cityManagement),25#驾照考试监考员行为检测事件(InvigilatorBehaviorEvent),26#车位检测(PackingSpaceRecognition),27#道路养护(roadMaint),28#水质检测数据(waterQualityDetection),29#水尺水位检测事件(GaugeReadingEvent)], desc:dataType为1对应violationType违法类型(字典)dataType为2对应violationType事件类型(字典);dataType为3对应violationType取证类型(字典),12#船舶航道或者航向角偏移检测对应搜索数据为ShipChannelAbnormal-->
            /**
             * <!--req, string, 违法类型, dep:and,{$.DataOperation.searchCond.criteria.dataType,be,0},{$.DataOperation.searchCond.criteria.dataType,lt,8},
             * desc:对应索引(字典),支持多选（无该字段或-1：全部）
             * 若dataType为0，该字段值为0;（代表着dataType为卡口数据时，是不存在违法类型的。  因此violationType值强制性赋值为0）。
             * 若dataType为1可通过获取违法字典动态获取取值/ISAPI/ITC/illegalDictionary,若有多个,数字索引中间用逗号间隔;;
             * 若dataType为2时对应交通事件类型字典,输入为事件对应的字符串（如：abandonedObject，pedestrian等）,不是数字索引,若有多个,字符串中间用逗号间隔;
             * 若dataType为3时可通过获取违法字典动态获取取值/ISAPI/ITC/EvidenceDictionary,若有多个,数字索引中间用逗号间隔;
             * 若dataType为6,7时该字段不赋值;-->
             */
            parameter.Add("violationType", "0");
            parameter.Add("channel", "");       //<!--req, int, 通道, range:[1,12], desc:无该字段:全部-->
            parameter.Add("plateType", "");     //<!--req, enum, 车牌类型, subType:int, [0#标准民用车与军车,1#02式民用车牌,2#武警车,3#警车,4#民用车双行尾牌,5#使馆车牌,6#农用车牌,7#摩托车牌,8#新能源车牌,255#其他]-->
            parameter.Add("plateColor", "");    //<!--req, enum, 车牌颜色, subType:int, [0#蓝色,1#黄色,2#白色,3#黑色,4#绿色,5#民航黑色,6#民航绿色,7#红色,8#新能源绿色,9#新能源黄绿色,16#黄绿色,17#渐变绿色,255#其他]-->
            parameter.Add("direction", "");     //<!--opt, enum, 监测点方向, subType:int, [1#上行,2#下行,3#双向,4#由东向西,5#由南向北,6#由西向东,7#由北向南,8#其他]-->
            parameter.Add("trafficSurveyVehicleType", "");      //<!--ro, opt, enum, 交调车辆类型, subType:int, [0#未知,1#中小客车,2#大客车,3#小型货车,4#中型货车,5#大型货车,6#特大型货车,7#集装箱货车,8#摩托车,9#拖拉机]-->
            parameter.Add("plate", "");     //<!--req, string, 车牌, range:[1,32]-->
            parameter.Add("speedMin", "");      //<!--opt, int, 最小速度-->
            parameter.Add("speedMax", "");      //<!--opt, int, 最大速度-->
            parameter.Add("vehicleType", "");   //<!--opt, enum, 车辆大类, subType:string, [0#其它车型,1#小型车,2#大型车,3#行人触发,4#二轮车触发,5#三轮车触发]-->
            parameter.Add("vehicleColor", "");  //<!--opt, enum, 车辆颜色, subType:int, [0#黑,1#白,2#银,3#灰,4#黑,5#红,6#深蓝,7#蓝,8#黄,9#绿,10#棕,11#粉,12#紫,13#深灰,14#青,15#橙,255#其他]-->
            parameter.Add("laneNo", "");        //<!--opt, int, 车道号-->
            parameter.Add("surveilType", "0");  //<!--req, enum, 监控类型, subType:int, [0#全部,1#授权名单数据,2#非授权名单数据]-->
            parameter.Add("romoteHost", "");    //<!--req, int, 远程主机, range:[1,4], desc:无该字段：全部-->
            parameter.Add("analysised", "true");    //<!--opt, bool, 分析状态, desc:false-未分析,true-已分析-->
            parameter.Add("matchedResult", "");     //<!--opt, enum, 匹配结果, subType:string, [videoData#视频数据(没有匹配电子车牌或者OBU的卡口数据),RFData#单独的电子车牌数据,fuseData#卡口电子车牌融合数据(匹配到电子车牌的卡口数据),OBUFuseData#OBU融合数据(匹配到OBU信息的卡口数据)], dep:and,{$.DataOperation.searchCond.criteria.dataType,eq,0}, desc:当dataType=0卡口时，本参数有效，注意：当查询单独的电子车牌数据(ePlateResult)时，需要特殊处理，即dataType=0，matchedResult=RFData，其他的单独数据都通过当dataType区分，如dataType=23查询单独的OBU数据-->
            parameter.Add("tollRoadVehicleSeries", "");     //<!--ro, opt, enum, 收费公路车辆系列, subType:int, [1#客车,2#货车,3#专项作业车], desc:按《JT-T 489-2019 收费公路车辆通行费车型分类》,需与tollRoadVehicleType组合使用-->
            parameter.Add("tollRoadVehicleType", "");       //<!--ro, opt, enum, 收费公路车辆类型, subType:int, [1#1类,2#2类,3#3类,4#4类,5#5类,6#6类], desc:按《JT-T 489-2019 收费公路车辆通行费车型分类》,需与tollRoadVehicleSeries组合使用-->
            parameter.Add("axleType", "");      //<!--req, enum, 国内车辆收费标准轴型, subType:int, [0#未知,11#2轴货车/2轴客车,12#2轴载货汽车/2轴客车,122#3轴中置轴挂车列车/3轴铰接列车/3轴客车,15#3轴载货汽车15型号,112#3轴载货汽车112型号/3轴客车,125#4轴中置轴挂车列车125型号/4轴铰接列车/4轴客车,152#4轴中置轴挂车列车152型号/4轴客车,1222#4轴全挂汽车列车/4轴客车,115#4轴载货汽车/4轴客车,155#5轴中置轴挂车列车155型号/5轴铰链列车155型号/5轴客车,1125#5轴中置轴挂车列车1125型号/5轴铰链列车1125型号/5轴客车,129#5轴铰链列车129型号/5轴客车,1152#5轴全挂汽车列车1522型号/5轴客车,11222#5轴全挂汽车列车11222型号/5轴客车,159#6轴中置轴挂车列车159型号/6轴中置轴挂车列车159-2型号/6轴铰链列车159-3型号/6轴铰链列车159-4型号/6轴客车,1155#6轴中置轴挂车列车1155-1型号/6轴中置轴挂车列车1155-2型号/6轴客车,1129#6轴铰链列车1129型号/6轴客车,11522#6轴全挂车11522-1型号/6轴全挂车11522-2型号/6轴客车]-->
            parameter.Add("dangmark", "all");   //<!--opt, enum, 危险品车, subType:string, [unknown#未知,yes#是,no#否,all#全部]-->
            parameter.Add("sendFlag", "");      //<!--req, enum, 发送标识, subType:string, [0#尚未发送,1#发送成功,2#无需发送], desc:无该字段：全部-->
            parameter.Add("searchResultPosition", "0");     //<!--req, int, 查询起始位置-->
            parameter.Add("maxResults", "20");      //<!--req, int, 本次查询条数-->
            parameter.Add("vehicleSubTypeList", "");    //<!--opt, array, 车辆类型查询条件列表, subType:object-->

            string strInbuff = ConfigFileUtil.GetReqBodyFromTemplate("\\conf\\ITC\\TrafficDataParam.xml", parameter);
            stdXMLConfig(lUserID, searchDataUrl, strInbuff);
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
            pOutputXml.lpOutBuffer = Marshal.AllocHGlobal(500 * 1024);    //输出缓冲区，如果接口调用失败提示错误码43，需要增大输出缓冲区
            pOutputXml.dwOutBufferSize = 500 * 1024;
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
