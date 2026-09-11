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
    class DoorManage
    {
        public static void controlGateway(int lUserID, int lGatewayIndex, int dwStaic)
        {
            bool b_Gate = CHCNetSDK.NET_DVR_ControlGateway(lUserID, lGatewayIndex, dwStaic);
            if (b_Gate == false)
            {
                Console.WriteLine("NET_DVR_ControlGateway远程控梯失败，错误码为" + CHCNetSDK.NET_DVR_GetLastError());
            }
            else
            {
                Console.WriteLine("远程控梯成功");
            }
        }

        public static void GetAndSetFloorCfg(int lUserID, int floor)
        {
            var struFloorCfg = new CHCNetSDK.NET_DVR_DOOR_CFG
            {
                dwSize = (uint)Marshal.SizeOf(typeof(CHCNetSDK.NET_DVR_DOOR_CFG))
            };
            IntPtr pStruFloorCfg = Marshal.AllocHGlobal(Marshal.SizeOf(struFloorCfg));
            Marshal.StructureToPtr(struFloorCfg, pStruFloorCfg, false);

            try
            {
                uint bytesReturned = 0;
                bool bGet = CHCNetSDK.NET_DVR_GetDVRConfig(
                    lUserID,
                    CHCNetSDK.NET_DVR_GET_DOOR_CFG,
                    1,
                    pStruFloorCfg,
                    struFloorCfg.dwSize,
                    ref bytesReturned);
                if (!bGet)
                {
                    uint errorCode = CHCNetSDK.NET_DVR_GetLastError();
                    Console.WriteLine("获取梯控楼层参数失败，错误码为" + errorCode);
                    return;
                }
                struFloorCfg = (CHCNetSDK.NET_DVR_DOOR_CFG)Marshal.PtrToStructure(pStruFloorCfg, typeof(CHCNetSDK.NET_DVR_DOOR_CFG));
                Console.WriteLine("获取梯控楼层参数成功");
                Console.WriteLine("楼层名称：" + struFloorCfg.byDoorName);
                Console.WriteLine("楼层继电器动作时间:" + struFloorCfg.byOpenDuration);
                Console.WriteLine("关门延迟时间:" + struFloorCfg.byDisabledOpenDuration);
                Console.WriteLine("梯控访客延迟时间:" + struFloorCfg.byLadderControlDelayTime);

                // 设置梯控楼层参数
                Encoding gbk = Encoding.GetEncoding("GBK");
                string newName = "floor111";
                byte[] nameBytes = gbk.GetBytes(newName);
                Marshal.StructureToPtr(struFloorCfg, pStruFloorCfg, true);
                bool bSet = CHCNetSDK.NET_DVR_SetDVRConfig(
                    lUserID,
                    CHCNetSDK.NET_DVR_SET_DOOR_CFG,
                    1,
                    pStruFloorCfg,
                    struFloorCfg.dwSize);
                if (!bSet)
                {
                    uint errorCode = CHCNetSDK.NET_DVR_GetLastError();
                    Console.WriteLine("设置梯控楼层参数失败，错误码为：" + errorCode);
                }
                else
                {
                    Console.WriteLine("设置梯控楼层参数成功！！！");
                }
            }
            finally
            {
                Marshal.FreeHGlobal(pStruFloorCfg);
            }
        }       

        public static void ConfigureElevatorTemplate(int lUserID, int iDoorTemplateNo, int floorID)
        {
            var doorStatusPlan = new CHCNetSDK.NET_DVR_DOOR_STATUS_PLAN
            {
                dwSize = (uint)Marshal.SizeOf(typeof(CHCNetSDK.NET_DVR_DOOR_STATUS_PLAN)),
                dwTemplateNo = (uint)iDoorTemplateNo,
                byRes = new byte[64]
            };
            Array.Clear(doorStatusPlan.byRes, 0, doorStatusPlan.byRes.Length);
            IntPtr ptrDoorStatusPlan = Marshal.AllocHGlobal(Marshal.SizeOf(doorStatusPlan));
            try
            {
                Marshal.StructureToPtr(doorStatusPlan, ptrDoorStatusPlan, false);
                if (!CHCNetSDK.NET_DVR_SetDVRConfig(
                    lUserID,
                    (uint)CHCNetSDK.NET_DVR_SET_DOOR_STATUS_PLAN,
                    floorID,
                    ptrDoorStatusPlan,
                    doorStatusPlan.dwSize))
                {
                    Console.WriteLine("设置梯控计划参数失败: " + CHCNetSDK.NET_DVR_GetLastError());
                    return;
                }
                Console.WriteLine("设置梯控计划参数成功");
            }
            finally
            {
                Marshal.FreeHGlobal(ptrDoorStatusPlan);
            }
            var doorTemplate = new CHCNetSDK.NET_DVR_PLAN_TEMPLATE();
            doorTemplate.Init();
            doorTemplate.dwSize = (uint)Marshal.SizeOf(typeof(CHCNetSDK.NET_DVR_PLAN_TEMPLATE));
            doorTemplate.byEnable = 1;
            doorTemplate.dwWeekPlanNo = 1;
            try
            {
                byte[] templateNameBytes = Encoding.GetEncoding("GBK").GetBytes("ElevatorTemplatePlan");
                Array.Clear(doorTemplate.byTemplateName, 0, doorTemplate.byTemplateName.Length);
                Array.Copy(templateNameBytes, doorTemplate.byTemplateName,
                          Math.Min(templateNameBytes.Length, doorTemplate.byTemplateName.Length));
            }
            catch (Exception ex)
            {
                Console.WriteLine("设置模板名称失败: " + ex.Message);
                return;
            }
            // 初始化假日组
            for (int i = 0; i < doorTemplate.dwHolidayGroupNo.Length; i++)
            {
                doorTemplate.dwHolidayGroupNo[i] = 0;
            }
            IntPtr ptrDoorTemplate = Marshal.AllocHGlobal(Marshal.SizeOf(doorTemplate));
            try
            {
                Marshal.StructureToPtr(doorTemplate, ptrDoorTemplate, false);
                if (!CHCNetSDK.NET_DVR_SetDVRConfig(
                    lUserID,
                    (uint)CHCNetSDK.NET_DVR_SET_DOOR_STATUS_PLAN_TEMPLATE,
                    iDoorTemplateNo,
                    ptrDoorTemplate,
                    doorTemplate.dwSize))
                {
                    Console.WriteLine("设置梯控计划模板失败: " + CHCNetSDK.NET_DVR_GetLastError());
                    return;
                }
                Console.WriteLine("设置梯控计划模板成功");
            }
            finally
            {
                Marshal.FreeHGlobal(ptrDoorTemplate);
            }
            var weekPlanCfg = new CHCNetSDK.NET_DVR_WEEK_PLAN_CFG();
            weekPlanCfg.Init();
            weekPlanCfg.dwSize = (uint)Marshal.SizeOf(typeof(CHCNetSDK.NET_DVR_WEEK_PLAN_CFG));
            weekPlanCfg.byEnable = 1;

            // 初始化所有时间段（禁用）
            const int MAX_DAYS = 7;
            const int MAX_TIMESEGMENT_PER_DAY = 8;
            for (int dayIndex = 0; dayIndex < MAX_DAYS; dayIndex++)
            {
                for (int segmentIndex = 0; segmentIndex < MAX_TIMESEGMENT_PER_DAY; segmentIndex++)
                {
                    int index = dayIndex * MAX_TIMESEGMENT_PER_DAY + segmentIndex;
                    weekPlanCfg.struPlanCfg[index].byEnable = 0;
                    weekPlanCfg.struPlanCfg[index].byDoorStatus = 0;    // 0-invalid
                    weekPlanCfg.struPlanCfg[index].byVerifyMode = 0;    // 0-invalid
                    weekPlanCfg.struPlanCfg[index].struTimeSegment.struBeginTime.byHour = 0;
                    weekPlanCfg.struPlanCfg[index].struTimeSegment.struBeginTime.byMinute = 0;
                    weekPlanCfg.struPlanCfg[index].struTimeSegment.struBeginTime.bySecond = 0;
                    weekPlanCfg.struPlanCfg[index].struTimeSegment.struEndTime.byHour = 0;
                    weekPlanCfg.struPlanCfg[index].struTimeSegment.struEndTime.byMinute = 0;
                    weekPlanCfg.struPlanCfg[index].struTimeSegment.struEndTime.bySecond = 0;
                }
            }

            // 设置一周7天，每天第一个时间段为24小时有效（梯控自由状态）
            for (int dayIndex = 0; dayIndex < MAX_DAYS; dayIndex++)
            {
                int index = dayIndex * MAX_TIMESEGMENT_PER_DAY;
                weekPlanCfg.struPlanCfg[index].byEnable = 1;
                weekPlanCfg.struPlanCfg[index].byDoorStatus = 1;    // 1-always open (free)
                weekPlanCfg.struPlanCfg[index].byVerifyMode = 1;    // 1-swipe card
                weekPlanCfg.struPlanCfg[index].struTimeSegment.struBeginTime.byHour = 0;
                weekPlanCfg.struPlanCfg[index].struTimeSegment.struBeginTime.byMinute = 0;
                weekPlanCfg.struPlanCfg[index].struTimeSegment.struBeginTime.bySecond = 0;
                weekPlanCfg.struPlanCfg[index].struTimeSegment.struEndTime.byHour = 23;
                weekPlanCfg.struPlanCfg[index].struTimeSegment.struEndTime.byMinute = 59;
                weekPlanCfg.struPlanCfg[index].struTimeSegment.struEndTime.bySecond = 59;
            }

            IntPtr ptrWeekPlanCfg = Marshal.AllocHGlobal(Marshal.SizeOf(weekPlanCfg));
            try
            {
                Marshal.StructureToPtr(weekPlanCfg, ptrWeekPlanCfg, false);
                if (!CHCNetSDK.NET_DVR_SetDVRConfig(
                    lUserID,
                    (uint)CHCNetSDK.NET_DVR_SET_WEEK_PLAN_CFG,
                    1,
                    ptrWeekPlanCfg,
                    weekPlanCfg.dwSize))
                {
                    Console.WriteLine("设置周计划失败: " + CHCNetSDK.NET_DVR_GetLastError());
                    return;
                }
                Console.WriteLine("设置周计划成功");
            }
            finally
            {
                Marshal.FreeHGlobal(ptrWeekPlanCfg);
            }
        }
    }
}
