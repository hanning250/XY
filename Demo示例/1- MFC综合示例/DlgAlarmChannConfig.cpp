// DlgAlarmChannConfig.cpp : 实现文件
//
#include "afxcmn.h"
#include "stdafx.h"
#include "ClientDemo.h"
#include "DlgAlarmChannConfig.h"
#include "afxdialogex.h"
#include "ClientDemoDlg.h"

// DlgAlarmChannConfig 对话框

IMPLEMENT_DYNAMIC(DlgAlarmChannConfig, CDialogEx)

DlgAlarmChannConfig::DlgAlarmChannConfig(CWnd* pParent /*=NULL*/)
: CDialogEx(DlgAlarmChannConfig::IDD, pParent)
, m_lAlarmHandle(-1)
, m_iDeviceIndex(-1)
, m_bDeviceSupport(FALSE)
{

}

DlgAlarmChannConfig::~DlgAlarmChannConfig()
{
	if (m_lAlarmHandle >= 0)
	{
		NET_DVR_CloseAlarmChan(m_lAlarmHandle);
		m_lAlarmHandle = -1;
	}
}

void DlgAlarmChannConfig::DoDataExchange(CDataExchange* pDX)
{
	CDialogEx::DoDataExchange(pDX);
	DDX_Control(pDX, IDC_LIST_ALARMCHAN, m_listAlarmChan);
	DDX_Control(pDX, IDC_EDIT_ALARMCHAN_CHANGE_INFO, m_editChangeInfo);
}


BEGIN_MESSAGE_MAP(DlgAlarmChannConfig, CDialogEx)
	ON_BN_CLICKED(IDOK, &DlgAlarmChannConfig::OnBnClickedOk)
END_MESSAGE_MAP()


// DlgAlarmChannConfig 消息处理程序

BOOL DlgAlarmChannConfig::OnInitDialog()
{
	CDialogEx::OnInitDialog();

	// 初始化列表控件
	m_listAlarmChan.SetExtendedStyle(LVS_EX_FULLROWSELECT | LVS_EX_GRIDLINES);
	m_listAlarmChan.InsertColumn(0, _T("IPID"), LVCFMT_LEFT, 80);
	//m_listAlarmChan.InsertColumn(1, _T("子设备视频通道号"), LVCFMT_LEFT, 100);
	m_listAlarmChan.InsertColumn(1, _T("报警输入通道号"), LVCFMT_LEFT, 120);
	m_listAlarmChan.InsertColumn(2, _T("报警输出通道号"), LVCFMT_LEFT, 120);

	// 设置控件初始状态
	//GetDlgItem(IDOK)->EnableWindow(FALSE);
	GetDlgItem(IDC_EDIT_ALARMCHAN_CHANGE_INFO)->SetWindowText(_T(""));

	OnBnClickedOk();//获取

	return TRUE;  // return TRUE unless you set the focus to a control
}

void DlgAlarmChannConfig::OnBnClickedOk()
{
	// TODO:  在此添加控件通知处理程序代码
	if (m_iDeviceIndex < 0)
	{
		AfxMessageBox(_T("请先登录设备！"));
		return;
	}

	CheckDeviceSupport();
	if (!m_bDeviceSupport)
	{
		AfxMessageBox(_T("当前设备不支持报警通道功能！"));
		return;
	}

	SetupAlarmSubscribe();
	GetIPIDChannelRelation();
	//CDialogEx::OnOK();
}

void DlgAlarmChannConfig::CheckDeviceSupport()
{
	m_bDeviceSupport = FALSE;

	if (m_iDeviceIndex < 0 || m_iDeviceIndex >= MAX_DEVICES)
	{
		return;
	}

	// 检查设备是否支持报警输入V40和视频数字通道
	if (/*(g_struDeviceInfo[m_iDeviceIndex].bySupport3 & 0x4) == 1 &&*/
		g_struDeviceInfo[m_iDeviceIndex].iIPChanNum > 0)
	{
		m_bDeviceSupport = TRUE;
	}
}

void DlgAlarmChannConfig::GetIPIDChannelRelation()
{
	if (m_iDeviceIndex < 0 || m_iDeviceIndex >= MAX_DEVICES)
	{
		return;
	}

	// 清空列表
	m_listAlarmChan.DeleteAllItems();

	// 获取IP资源信息
	NET_DVR_IPPARACFG_V40 struIPParaCfgV40 = { 0 };
	DWORD dwReturned = 0;
	BOOL bRet = NET_DVR_GetDVRConfig(g_struDeviceInfo[m_iDeviceIndex].lLoginID, NET_DVR_GET_IPPARACFG_V40, 0, &struIPParaCfgV40, sizeof(struIPParaCfgV40), &dwReturned);
	if (!bRet)
	{
		DWORD dwErr = NET_DVR_GetLastError();
		CString strErr;
		strErr.Format(_T("获取IP参数配置失败，错误码：%d"), dwErr);
		AfxMessageBox(strErr);
		return;
	}

	// 获取报警输入配置
	NET_DVR_IPALARMINCFG_V40 struIPAlarmInCfgV40 = { 0 };
	bRet = NET_DVR_GetDVRConfig(g_struDeviceInfo[m_iDeviceIndex].lLoginID, NET_DVR_GET_IPALARMINCFG_V40, 0, &struIPAlarmInCfgV40, sizeof(struIPAlarmInCfgV40), &dwReturned);
	if (!bRet)
	{
		DWORD dwErr = NET_DVR_GetLastError();
		CString strErr;
		strErr.Format(_T("获取IP报警输入配置失败，错误码：%d"), dwErr);
		AfxMessageBox(strErr);
		return;
	}

	// 获取报警输出配置
	NET_DVR_IPALARMOUTCFG_V40 struIPAlarmOutCfgV40 = { 0 };
	bRet = NET_DVR_GetDVRConfig(g_struDeviceInfo[m_iDeviceIndex].lLoginID, NET_DVR_GET_IPALARMOUTCFG_V40, 0, &struIPAlarmOutCfgV40, sizeof(struIPAlarmOutCfgV40), &dwReturned);
	if (!bRet)
	{
		DWORD dwErr = NET_DVR_GetLastError();
		CString strErr;
		strErr.Format(_T("获取IP报警输出配置失败，错误码：%d"), dwErr);
		AfxMessageBox(strErr);
		return;
	}

	int dwIPIDTemp = 0;
	// 建立IPID与通道号的映射关系
	// 首先获取IPID与视频通道号的映射
	for (int i = 0; i < MAX_CHANNUM_V40; i++)
	{
		if (i >= struIPParaCfgV40.dwAChanNum + struIPParaCfgV40.dwDChanNum)
			break;

		// 获取IPID
		DWORD dwIPID = struIPParaCfgV40.struStreamMode[i].uGetStream.struChanInfo.byIPID +
			(struIPParaCfgV40.struStreamMode[i].uGetStream.struChanInfo.byIPIDHigh << 8);

		// 获取视频通道号
		//DWORD dwChannel = struIPParaCfgV40.struStreamMode[i].uGetStream.struChanInfo.byChannel;

		//当前dwIPID不等于0且dwIPID不等于上次存储的dwIPID，则进行报警通道的查询
		if (dwIPID != 0 && dwIPIDTemp != dwIPID)
		{
			dwIPIDTemp = dwIPID;
			DWORD dwAlarmIn[64] = { 0 };//单台子设备报警输入通道最大不会超过64
			DWORD dwAlarmOut[64] = { 0 };//单台子设备报警输出通道最大不会超过64
			int iAlarmInNum = 0;
			int iAlarmOutNum = 0;

			// 查找该IPID对应的报警输入通道
			for (int j = 0; j < 4096; j++)
			{
				if (struIPAlarmInCfgV40.struIPAlarmInInfo[j].dwIPID == dwIPID &&
					struIPAlarmInCfgV40.struIPAlarmInInfo[j].dwAlarmIn != 0 && iAlarmInNum<64)
				{
					dwAlarmIn[iAlarmInNum] = g_struDeviceInfo[m_iDeviceIndex].iAlarmInNum + j + 1;
					iAlarmInNum++;
					//break;
				}
			}

			// 查找该IPID对应的报警输出通道
			for (int j = 0; j < 4096; j++)
			{
				if (struIPAlarmOutCfgV40.struIPAlarmOutInfo[j].dwIPID == dwIPID &&
					struIPAlarmOutCfgV40.struIPAlarmOutInfo[j].dwAlarmOut != 0 && iAlarmOutNum<64)
				{
					dwAlarmOut[iAlarmOutNum] = g_struDeviceInfo[m_iDeviceIndex].iAlarmOutNum + j + 1;
					iAlarmOutNum++;
					//break;
				}
			}


			// 该IPID对应的报警输入、输出通道添加到列表
			if (iAlarmInNum != 0 || iAlarmOutNum != 0)
			{
				// 如果 iAlarmInNum 大于 iAlarmOutNum，则取前者，否则取后者
				int iMaxAlarmNum = (iAlarmInNum > iAlarmOutNum) ? iAlarmInNum : iAlarmOutNum;

				for (int j = 0; j < iMaxAlarmNum; j++)
				{
					int nItem = m_listAlarmChan.InsertItem(m_listAlarmChan.GetItemCount(), _T(""));
					CString strIPID;
					strIPID.Format(_T("%d"), dwIPID);
					m_listAlarmChan.SetItemText(nItem, 0, strIPID);

					/*
					CString strChannel;
					strChannel.Format(_T("%d"), dwChannel);
					m_listAlarmChan.SetItemText(nItem, 1, strChannel);
					*/
					CString strAlarmIn;
					strAlarmIn.Format(_T("%d"), dwAlarmIn[j]);
					m_listAlarmChan.SetItemText(nItem, 1, strAlarmIn);

					CString strAlarmOut;
					strAlarmOut.Format(_T("%d"), dwAlarmOut[j]);
					m_listAlarmChan.SetItemText(nItem, 2, strAlarmOut);
				}

				//添加列表完成，需初始化
				memset(dwAlarmIn, 0, sizeof(dwAlarmIn));
				memset(dwAlarmOut, 0, sizeof(dwAlarmOut));
				iAlarmInNum = 0;
				iAlarmOutNum = 0;
			}
		}
	}
}

void DlgAlarmChannConfig::ProcessDeviceStatusChanged(char* szJsonData)
{
	// 当接收到设备状态变化事件时刷新列表
	CString strInfo;
	SYSTEMTIME st;
	GetLocalTime(&st);
	strInfo.Format(_T("[%04d-%02d-%02d %02d:%02d:%02d] 已经收到设备状态变化事件，上述表格将自动刷新！"),
		st.wYear, st.wMonth, st.wDay, st.wHour, st.wMinute, st.wSecond);
	m_editChangeInfo.SetWindowText(strInfo);

	GetIPIDChannelRelation();
}

void DlgAlarmChannConfig::SetupAlarmSubscribe()
{

	if (m_lAlarmHandle != -1)
	{
		return;
	}

	// 设置报警回调函数
	// 注意：NET_DVR_SetDVRMessageCallBack_V50需要三个参数：索引(int)，回调函数指针，用户数据指针
	NET_DVR_SetDVRMessageCallBack_V50(0, (MSGCallBack)OnAlarmCallback, this);

	// 建立报警上传通道 - 使用正确的API调用方式，传递XML数据
	NET_DVR_SETUPALARM_PARAM_V50 struSetupAlarmParam = { 0 };
	struSetupAlarmParam.dwSize = sizeof(struSetupAlarmParam);

	// 使用更简单的处理方式，不进行复杂的字符串转换
	// 直接使用字面量字符串
	const char* szXml = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
		"<SubscribeEvent xmlns=\"http://www.isapi.org/ver20/XMLSchema\" version=\"2.0\">\n"
		"  <eventMode>all</eventMode>\n"
		"  <ChangedUploadSub>\n"
		"    <StatusSub>\n"
		"      <all>true</all>\n"
		"    </StatusSub>\n"
		"  </ChangedUploadSub>\n"
		"</SubscribeEvent>";

	m_lAlarmHandle = NET_DVR_SetupAlarmChan_V50(g_struDeviceInfo[m_iDeviceIndex].lLoginID, &struSetupAlarmParam, (char*)szXml, strlen(szXml));
	if (m_lAlarmHandle < 0)
	{
		DWORD dwErr = NET_DVR_GetLastError();
		CString strErr;
		strErr.Format(_T("建立报警上传通道失败，错误码：%d"), dwErr);
		AfxMessageBox(strErr);
	}
	else
	{
		AfxMessageBox(_T("成功建立报警订阅通道！"));
	}
}

void CALLBACK OnAlarmCallback(LONG lCommand, NET_DVR_ALARMER *pAlarmer, char *pAlarmInfo, DWORD dwBufLen, void* pUser)
{
	DlgAlarmChannConfig* pDlg = (DlgAlarmChannConfig*)pUser;
	if (pDlg == NULL)
	{
		return;
	}

	if (lCommand == COMM_DEV_STATUS_CHANGED)
	{
		pDlg->ProcessDeviceStatusChanged(pAlarmInfo);
	}
}
