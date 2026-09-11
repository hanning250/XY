/**********************************************************
FileName:    DlgUpgrade.cpp
Description: update dialogbox     
Date:        2008/05/17
Note: 		<Global>struct, macro refer to GeneralDef.h, global variants and API refer to ClientDemo.cpp   
Modification History:      
    <version> <time>         <desc>
    <1.0    > <2008/05/17>       <created>
***********************************************************/

#include "stdafx.h"
#include "ClientDemo.h"
#include "DlgUpgrade.h"
#include "DlgUpgradeSelectDev.h"
#include ".\dlgupgrade.h"


// CDlgUpgrade dialog
/*********************************************************
  Function:	CDlgUpgrade
  Desc:		Constructor
  Input:	
  Output:	
  Return:	
**********************************************************/
IMPLEMENT_DYNAMIC(CDlgUpgrade, CDialog)
CDlgUpgrade::CDlgUpgrade(CWnd* pParent /*=NULL*/)
	: CDialog(CDlgUpgrade::IDD, pParent)
	, m_csUpgradeFile(_T(""))
    , m_csUpgradeURL(_T(""))
	, m_csUpgradeStat(_T(""))
	, m_lUpgradeHandle(0)
	, m_lServerID(-1)
	, m_lChannel(-1)
	, m_lpUpgradeTimer(NULL)
	, m_bUpgrade(FALSE)
    , m_dwAcsNo(0)
    , m_iPreValidateHeaderLength(0)
    , m_bNeedForceUpgrade(FALSE)
{
}

/*********************************************************
  Function:	~CDlgUpgrade
  Desc:		destructor
  Input:	
  Output:	
  Return:	
**********************************************************/
CDlgUpgrade::~CDlgUpgrade()
{
}

/*********************************************************
Function:	DoDataExchange
Desc:		the map between control and variable
Input:	
Output:	
Return:	
**********************************************************/
void CDlgUpgrade::DoDataExchange(CDataExchange* pDX)
{
    CDialog::DoDataExchange(pDX);
    //{{AFX_DATA_MAP(CDlgUpgrade)
    DDX_Control(pDX, IDC_PROGRESS_STEP, m_progressSub);
    DDX_Control(pDX, IDC_COMBO_CHAN, m_comboChan);
    DDX_Control(pDX, IDC_COMBO_UPGRADE_TYPE, m_comboUpgradeType);
    DDX_Control(pDX, IDC_COMBO_ENVIRONMENT, m_comboEnvironment);
    DDX_Control(pDX, IDC_PROGRESS_UPGRADE, m_progressUpgrade);
    DDX_Control(pDX, IDC_COMBO_CARD_TYPE, m_comboCardType);
    DDX_Control(pDX, IDC_COMBO_AUX_DEV, m_comboAuxDev);
    DDX_Text(pDX, IDC_EDIT_UPGRADE_FILE, m_csUpgradeFile);
    DDX_Text(pDX, IDC_EDIT_UPGRADE_URL, m_csUpgradeURL);
    DDX_Text(pDX, IDC_STATIC_UPGRADE, m_csUpgradeStat);
    DDX_Text(pDX, IDC_STATIC_STEP, m_csUpgradeStep);
    DDX_Check(pDX, IDC_CHK_FUZZYUPGRADE, m_bFuzzyUpgrade);
    DDX_Text(pDX, IDC_EDIT_ACS_NO, m_dwAcsNo);
    DDX_Text(pDX, IDC_EDT_UNIT_ID, m_csUnitID);
    DDX_Check(pDX, IDC_CHK_FORCE_UPGRADE, m_bForceUpgrade);
    //}}AFX_DATA_MAP
    DDX_Control(pDX, IDC_COMBO_LANGUAGE_TYPE, m_combolanguageType);
}


/*********************************************************
Function:	BEGIN_MESSAGE_MAP
Desc:		the map between control and function
Input:	
Output:	
Return:	
**********************************************************/
BEGIN_MESSAGE_MAP(CDlgUpgrade, CDialog)
	//{{AFX_MSG_MAP(CDlgUpgrade)	
	ON_BN_CLICKED(IDC_BTN_BROWSE_FILE, OnBnClickedBtnBrowseFile)
	ON_BN_CLICKED(IDC_BTN_UPGRADE, OnBnClickedBtnUpgrade)
	ON_BN_CLICKED(IDC_BTN_UPGRADE_EXIT, OnBnClickedBtnUpgradeExit)
	ON_WM_TIMER()
	ON_BN_CLICKED(IDC_BTN_SET_ENVIRO, OnBtnSetEnviro)
	ON_CBN_SELCHANGE(IDC_COMBO_UPGRADE_TYPE, OnSelchangeComboUpgradeType)
	ON_BN_CLICKED(IDC_BTN_GETUPGRADEINFO, OnBtnGetupgradeinfo)
	//}}AFX_MSG_MAP
	
    ON_BN_CLICKED(IDC_BTN_SELECT_DEV, &CDlgUpgrade::OnBnClickedBtnSelectDev)
    ON_BN_CLICKED(IDC_BTN_KEEP_UPGRATE, &CDlgUpgrade::OnBnClickedBtnKeepUpgrade)
    ON_BN_CLICKED(IDC_BTN_STOP_KEEP_UPGRATE, &CDlgUpgrade::OnBnClickedBtnStopKeepUpgrade)
    ON_BN_CLICKED(IDC_BTN_PRE_VALIDATE, &CDlgUpgrade::OnBnClickedBtnPreValidate)
END_MESSAGE_MAP()


// CDlgUpgrade message handlers
/*********************************************************
Function:	OnInitDialog
Desc:		Initialize the dialog
Input:	
Output:	
Return:	
**********************************************************/
BOOL CDlgUpgrade::OnInitDialog() 
{
	CDialog::OnInitDialog();

	// TODO: Add extra initialization here
	m_csUpgradeFile.Format("c:\\digicap");
	UpdateData(FALSE);
	m_bUpgrade = FALSE;
	m_progressUpgrade.SetRange(0,100);
	m_progressUpgrade.SetPos(0);
	m_progressUpgrade.ShowWindow(SW_HIDE);
	m_comboEnvironment.SetCurSel(0);

    m_comboUpgradeType.ResetContent();
    m_comboUpgradeType.AddString("DVR");
    m_comboUpgradeType.AddString("Adapter");
    m_comboUpgradeType.AddString("Vca lib");
    m_comboUpgradeType.AddString("ACS");
	m_comboUpgradeType.AddString("IDS");
	m_comboUpgradeType.AddString("LED");
    m_comboUpgradeType.AddString("Intelligent");
    m_comboUpgradeType.AddString("CustomURL");
    m_comboUpgradeType.AddString("DVR-PreValidate");
    m_comboUpgradeType.SetCurSel(0);
	OnSelchangeComboUpgradeType();
    
    m_comboAuxDev.ResetContent();
    m_comboAuxDev.AddString("Keyboard");
    m_comboAuxDev.AddString("Movement");
	m_comboAuxDev.AddString("NetModule");
    m_comboAuxDev.AddString("Router");
    m_comboAuxDev.AddString("Zone");
    m_comboAuxDev.AddString("RS485");
    m_comboAuxDev.AddString("TempCtrl");
    m_comboAuxDev.AddString("ElectricLock");
    m_comboAuxDev.AddString("NetPortPowerSupply");
    m_comboAuxDev.SetCurSel(0);

    //界面是否显示二次确认按钮 
    if (IsSupPreValidate()) 
    {
        GetDlgItem(IDC_BTN_PRE_VALIDATE)->EnableWindow(SW_SHOW);
        GetDlgItem(IDC_COMBO_LANGUAGE_TYPE)->EnableWindow(SW_SHOW);
    }
    else
    {
        GetDlgItem(IDC_BTN_PRE_VALIDATE)->EnableWindow(SW_HIDE);
        GetDlgItem(IDC_COMBO_LANGUAGE_TYPE)->EnableWindow(SW_HIDE);
    }

   
    GetDlgItem(IDC_CHK_FORCE_UPGRADE)->ShowWindow(SW_HIDE);
    memset(m_byUpgradeToken, 0, sizeof(m_byUpgradeToken));

	return TRUE;  // return TRUE unless you set the focus to a control
	// EXCEPTION: OCX Property Pages should return FALSE
}

/*********************************************************
  Function:	OnBnClickedBtnBrowseFile
  Desc:		browse update firmware
  Input:	
  Output:	
  Return:	
**********************************************************/
void CDlgUpgrade::OnBnClickedBtnBrowseFile()
{
	UpdateData(TRUE);
	if (m_bFuzzyUpgrade)
	{
		CString Str = F_GetDirectoryPath();
		if(Str != "")
		{
			m_csUpgradeFile = Str;
			UpdateData(FALSE);
		}
	} 
	else
	{
		static char szFilter[]="All File(*.*)|*.*||";
		CFileDialog dlg(TRUE,"*.*","digicap",OFN_HIDEREADONLY|OFN_OVERWRITEPROMPT,
			szFilter);
		if (dlg.DoModal()==IDOK)
		{
			m_csUpgradeFile = dlg.GetPathName();
			UpdateData(FALSE);
		}
	}	
}

CString CDlgUpgrade::F_GetDirectoryPath()
{
    LPITEMIDLIST pidlRoot = NULL;
    SHGetSpecialFolderLocation(m_hWnd, CSIDL_DRIVES, &pidlRoot);
    BROWSEINFO bi;   //必须传入的参数,下面就是这个结构的参数的初始化
    CString strDisplayName;   //用来得到,你选择的活页夹路径,相当于提供一个缓冲区
    bi.hwndOwner = GetSafeHwnd();   //得到父窗口Handle值
    bi.pidlRoot = pidlRoot;   //这个变量就是我们在上面得到的.
    bi.pszDisplayName = strDisplayName.GetBuffer(MAX_PATH + 1);   //得到缓冲区指针
    bi.lpszTitle = "文件夹";   //设置标题
    bi.ulFlags = BIF_RETURNONLYFSDIRS;   //设置标志
    bi.lpfn = NULL;
    bi.lParam = 0;
    bi.iImage = 0;   //上面这个是一些无关的参数的设置,最好设置起来,
    LPITEMIDLIST lpIDList = SHBrowseForFolder(&bi);	//打开对话框
    strDisplayName.ReleaseBuffer();   //和上面的GetBuffer()相对应
    char pPath[MAX_PATH];
    CString Str;
    if(lpIDList)
    {
        SHGetPathFromIDList(lpIDList, pPath);
        Str = pPath;
    }
	
    return Str;
}

/*********************************************************
  Function:	start update
  Input:	
  Output:	
  Return:	
**********************************************************/
void CDlgUpgrade::OnBnClickedBtnUpgrade()
{
    char szStatusBuf[ISAPI_STATUS_LEN];
    char szOutBuf[ISAPI_STATUS_LEN];

    NET_DVR_MULTI_ALARMIN_COND struAlarmCond = { 0 };
    struAlarmCond.dwSize = sizeof(struAlarmCond);
    for (int i = 0; i < 8; i++)
    {
        struAlarmCond.iZoneNo[i] = 1111;
    }
    for (int i = 8; i < MAX_MAX_ALARMIN_NUM; i++)
    {
        struAlarmCond.iZoneNo[i] = -1;
    }

    NET_DVR_STD_CONFIG struCfg = { 0 };
    struCfg.lpCondBuffer = &struAlarmCond;
    struCfg.dwCondSize = sizeof(struAlarmCond);
    struCfg.lpOutBuffer = szOutBuf;
    struCfg.dwOutSize = ISAPI_STATUS_LEN;
    memset(szStatusBuf, 0, ISAPI_STATUS_LEN);
    struCfg.lpStatusBuffer = szStatusBuf;
    struCfg.dwStatusSize = ISAPI_STATUS_LEN;

    int iErr = 0;
    //if (!NET_DVR_GetSTDConfig(m_lServerID, NET_DVR_GET_ALARMIN_PARAM_LIST_V50, &struCfg))
    //{
    //    iErr = NET_DVR_GetLastError();
    //}

	char m_szFileName[MAX_PATH];
    char szCustomURL[MAX_URL_LEN];

	UpdateData(TRUE);
	strcpy(m_szFileName,m_csUpgradeFile);
    strcpy(szCustomURL, m_csUpgradeURL);
    char szLan[128] = {0};
	/*
	CFile cFile;
	if (!cFile.Open(m_szFileName,NULL))
	{
		g_StringLanType(szLan, "打开文件失败或无此文件", "Open file failed or no this file");
		AfxMessageBox(szLan);
		return;
	}
	DWORD dwFileSize = (DWORD)cFile.GetLength();
	if (dwFileSize == 0)
	{
		g_StringLanType(szLan, "升级文件为空", "Upgrade file is empty");
		AfxMessageBox(szLan);
	}
	cFile.Close();
	*/
     
    if (m_comboUpgradeType.GetCurSel() == 0) // DVR upgrade 
    {
	    m_lUpgradeHandle = NET_DVR_Upgrade(m_lServerID, m_szFileName);
    }
    else if (m_comboUpgradeType.GetCurSel() == 1) // adapter upgrade
    {
        m_lUpgradeHandle = NET_DVR_AdapterUpgrade(m_lServerID, m_szFileName);
    }
    else if (m_comboUpgradeType.GetCurSel() == 2) // vca lib upgrade
    {
        m_lUpgradeHandle = NET_DVR_VcalibUpgrade(m_lServerID, m_comboChan.GetCurSel() + 1, m_szFileName);
    }
    else if (m_comboUpgradeType.GetCurSel() == 3)
    {
        DWORD dwDevNo = m_dwAcsNo;
        m_lUpgradeHandle = NET_DVR_Upgrade_V40(m_lServerID, ENUM_UPGRADE_ACS, m_szFileName, &dwDevNo, sizeof(dwDevNo));
    }
	else if (m_comboUpgradeType.GetCurSel() == 4)
	{
		NET_DVR_AUXILIARY_DEV_UPGRADE_PARAM struAuxiliaryDevUpgradeParam = {0};
		struAuxiliaryDevUpgradeParam.dwSize = sizeof(struAuxiliaryDevUpgradeParam);
		//struAuxiliaryDevUpgradeParam.byDevType = 0;//目前视频报警主机辅助设备类型只有键盘
        struAuxiliaryDevUpgradeParam.byDevType = m_comboAuxDev.GetCurSel();
		struAuxiliaryDevUpgradeParam.dwDevNo = m_comboChan.GetCurSel();
		m_lUpgradeHandle = NET_DVR_Upgrade_V40(m_lServerID, ENUM_UPGRADE_AUXILIARY_DEV, m_szFileName, &struAuxiliaryDevUpgradeParam, sizeof(struAuxiliaryDevUpgradeParam));
	}
	else if (m_comboUpgradeType.GetCurSel() == 5)
	{
		DWORD dwCardType = m_comboCardType.GetCurSel()+1;
		m_lUpgradeHandle = NET_DVR_Upgrade_V40(m_lServerID, ENUM_UPGRADE_LED, m_szFileName, &dwCardType, sizeof(dwCardType));
	}
    else if (m_comboUpgradeType.GetCurSel() == 6)
    {
        DWORD dwCardType = m_comboCardType.GetCurSel() + 1;
        NET_DVR_UPGRADE_PARAM struUpgradeParam = { 0 };
        struUpgradeParam.dwUpgradeType = ENUM_UPGRADE_INTELLIGENT;
        struUpgradeParam.sFileName = m_szFileName;
        char szUnitID[128] = { 0 };
        strncpy(szUnitID, (char*)m_csUnitID.GetBuffer(), 128);

        struUpgradeParam.pUnitIdList[0] = szUnitID;// "829282394af74ffca1a11d3d5c68e29b";
        m_lUpgradeHandle = NET_DVR_Upgrade_V50(m_lServerID, &struUpgradeParam);
    }
    else if (m_comboUpgradeType.GetCurSel() == 7)
    {
        NET_DVR_UPGRADE_PARAM struUpgradeParam = { 0 };
        struUpgradeParam.dwUpgradeType = ENUM_UPGRADE_CUSTOM;
        struUpgradeParam.sFileName = m_szFileName;
        //指定URL
        struUpgradeParam.sCustomURL = szCustomURL;
        struUpgradeParam.dwCustomURLLen = strlen(szCustomURL);

        m_lUpgradeHandle = NET_DVR_Upgrade_V50(m_lServerID, &struUpgradeParam);
    }
    else if (m_comboUpgradeType.GetCurSel() == 8)  //DVR方式 需要预校验&二次确认
    {
        NET_DVR_UPGRADE_PARAM struUpgradeParam = { 0 };
        struUpgradeParam.dwUpgradeType = ENUM_UPGRADE_DVR;
        struUpgradeParam.sFileName = m_szFileName;
        if (m_bForceUpgrade) //选择了强制升级,才会携带Token
        {
            //指定Token
            memcpy(struUpgradeParam.byUpgradeToken, m_byUpgradeToken, sizeof(m_byUpgradeToken));

        }
        m_lUpgradeHandle = NET_DVR_Upgrade_V50(m_lServerID, &struUpgradeParam);
    }
	if (m_lUpgradeHandle < 0)
	{
		g_pMainDlg->AddLog(m_iDeviceIndex, OPERATION_FAIL_T, "NET_DVR_Upgrade");
		g_StringLanType(szLan, "升级失败", "Upgrade failed");
		AfxMessageBox(szLan);
	}
	else
	{
        g_pMainDlg->AddLog(m_iDeviceIndex, OPERATION_SUCC_T, "NET_DVR_Upgrade");
		GetDlgItem(IDC_STATIC_UPGRADE)->ShowWindow(SW_SHOW);
		GetDlgItem(IDC_BTN_UPGRADE)->EnableWindow(FALSE);
		GetDlgItem(IDC_BTN_UPGRADE_EXIT)->EnableWindow(FALSE);
		GetDlgItem(IDC_BTN_BROWSE_FILE)->EnableWindow(FALSE);
		m_progressUpgrade.SetPos(0);
		m_progressUpgrade.ShowWindow(SW_SHOW);
		g_StringLanType(szLan, "状态：正在升级服务器，请等待......", "Status: Server is upgrading, please wait......");
		m_csUpgradeStat.Format(szLan);
		m_bUpgrade = TRUE;
		m_lpUpgradeTimer = SetTimer(UPGRADE_TIMER, 500, NULL);
		UpdateData(FALSE);
	}	
}

/*********************************************************
  Function:	OnBnClickedBtnUpgradeExit
  Desc:		exit update
  Input:	
  Output:	
  Return:	
**********************************************************/
void CDlgUpgrade::OnBnClickedBtnUpgradeExit()
{
	if (m_lpUpgradeTimer)
	{
		KillTimer(UPGRADE_TIMER);
	}
	CDialog::OnCancel();
}

/*********************************************************
  Function:	OnTimer
  Desc:		refresh update status timer
  Input:	
  Output:	
  Return:	
**********************************************************/
#if (_MSC_VER >= 1500)	//vs2008
void CDlgUpgrade::OnTimer(UINT_PTR nIDEvent)
#else
void CDlgUpgrade::OnTimer(UINT nIDEvent) 
#endif
{
	// TODO: Add your message handler code here and/or call default
	char szLan[128] = {0};
	if (nIDEvent == UPGRADE_TIMER)
	{
		if (m_bUpgrade)
		{
			int UpgradeStatic = NET_DVR_GetUpgradeState(m_lUpgradeHandle);
			DWORD dwError = NET_DVR_GetLastError();
			int iPos = NET_DVR_GetUpgradeProgress(m_lUpgradeHandle);
			
			LONG iSubProgress = -1;
			int iStep = NET_DVR_GetUpgradeStep(m_lUpgradeHandle, &iSubProgress);

			if(iStep != -1)
			{
				GetDlgItem(IDC_STATIC_STEP)->ShowWindow(SW_SHOW);
				GetDlgItem(IDC_PROGRESS_STEP)->ShowWindow(SW_SHOW);	
				m_progressSub.SetPos(iSubProgress);
				switch(iStep)
				{
				case STEP_READY:
					g_StringLanType(szLan, "正在准备升级", "Ready to upgrade file");
					m_csUpgradeStep.Format("%s", szLan);
					break;
				case STEP_RECV_DATA:
					g_StringLanType(szLan, "正在读取升级文件", "Receving upgrade file");
					m_csUpgradeStep.Format("%s", szLan);
					break;
				case STEP_UPGRADE:
					g_StringLanType(szLan, "正在升级系统", "Upgrading system");
					m_csUpgradeStep.Format("%s", szLan);
					break;
				case STEP_BACKUP:
					g_StringLanType(szLan, "正在备份系统", "Backuping system");
					m_csUpgradeStep.Format("%s", szLan);
					break;
				case STEP_SEARCH:
					g_StringLanType(szLan, "正在搜索升级文件", "Searching  upgrade file");
					m_csUpgradeStep.Format("%s", szLan);
					break;
				default:
					g_StringLanType(szLan, "未知阶段", "Unknow step");
					m_csUpgradeStep.Format("%s:%d", szLan, iStep);
					break;
				}
			}

			g_pMainDlg->AddLog(m_iDeviceIndex, OPERATION_SUCC_T, "NET_DVR_GetUpgradeProgress= [%d]",iPos);
			if (iPos >0)
			{
				m_progressUpgrade.SetPos(iPos);
			}
			if (UpgradeStatic == 2)
			{
				g_StringLanType(szLan, "状态：正在升级设备，请等待......", "Status: Device is upgrading, please wait......");
				m_csUpgradeStat.Format(szLan);
				UpdateData(FALSE);
			}
			else
			{
                bool modelFileNeedUpdate = false;
				switch (UpgradeStatic)
				{
				case -1:
					g_StringLanType(szLan, "升级失败", "Upgrade failed");
//					AfxMessageBox(szLan);			
					break;
                case 1:
                    if (true)
                    {
                        NET_DVR_XML_CONFIG_INPUT xmlInput = { 0 };
                        NET_DVR_XML_CONFIG_OUTPUT xmlOutput = { 0 };
                        xmlInput.dwSize = sizeof(NET_DVR_XML_CONFIG_INPUT);
                        xmlOutput.dwSize = sizeof(NET_DVR_XML_CONFIG_OUTPUT);
                        char *strUrl = "GET /ISAPI/ITC/AlgorithmsState\r\n";
                        xmlInput.lpRequestUrl = strUrl;
                        xmlInput.dwRequestUrlLen = strlen(strUrl);
                        xmlInput.lpInBuffer = NULL;
                        xmlInput.dwInBufferSize = 0;
                        xmlInput.dwRecvTimeOut = 1000;

                        char *pOutBuf = new char[5 * 1024];
                        memset(pOutBuf, 0, 5 * 1024);
                        xmlOutput.lpOutBuffer = pOutBuf;
                        xmlOutput.dwOutBufferSize = 5 * 1024;
                        if (NET_DVR_STDXMLConfig(m_lServerID, &xmlInput, &xmlOutput))
                        {
                            g_pMainDlg->AddLog(m_iDeviceIndex, OPERATION_SUCC_T, "NET_DVR_STDXMLConfig");
                            CString strRetXml = (const char*)xmlOutput.lpOutBuffer;
                            if (strRetXml.Find("modelFileNeedUpdate") > 0)
                            {
                                modelFileNeedUpdate = true;
                            }
                        }
                        else
                        {
                            g_pMainDlg->AddLog(m_iDeviceIndex, OPERATION_FAIL_T, "NET_DVR_STDXMLConfig");
                        }
                        delete[]pOutBuf;
                    }
                    if (m_comboUpgradeType.GetCurSel() == 4)
                    {
                        if (modelFileNeedUpdate)
                        {
                            g_StringLanType(szLan, "状态：升级设备成功并且需要升级模型文件", "Status:upgrade successfully and model file need update");
                        }
                        else
                        {
                            g_StringLanType(szLan, "状态：升级设备成功", "Status:upgrade successfully");
                        }
                    }
                    else
                    {
                        if (modelFileNeedUpdate)
                        {
                            g_StringLanType(szLan, "状态：升级设备成功,请升级模型文件并重启设备", "Status:upgrade successfully, update mode file and reboot please");
                        }
                        else
                        {
                            g_StringLanType(szLan, "状态：升级设备成功,请重启设备", "Status:upgrade successfully, reboot please");
                        }
                    }

					m_csUpgradeStat.Format(szLan);
					m_progressUpgrade.SetPos(100);
					break;			
				case 3:
					g_StringLanType(szLan, "状态：升级设备失败", "Status:upgrade failed");
					m_csUpgradeStat.Format(szLan);	
					break;
				case 4:
					g_StringLanType(szLan, "状态：从设备接收数据错误, 状态未知", "Status:get data with probrem from device, status unknown");
					m_csUpgradeStat.Format(szLan);					
					break;
				case 5:
					g_StringLanType(szLan, "状态：升级文件语言版本不匹配", "Status:Upgrade file language mismatch");
					m_csUpgradeStat.Format(szLan);				
					break;
				case 6:
					g_StringLanType(szLan, "状态：升级文件写flash文件失败", "Status:Upgrade file write Flash Fail!");
					m_csUpgradeStat.Format(szLan);				
					break;
                case 7:
                    g_StringLanType(szLan, "状态：升级包类型不匹配", "Status:Upgrade Pack Type Mismatch!");
                    m_csUpgradeStat.Format(szLan);				
					break;
                case 8:
                    g_StringLanType(szLan, "状态：升级包版本不匹配", "Status:Upgrade Pack Version Mismatch!");
                    m_csUpgradeStat.Format(szLan);				
					break;
                case 9:
                    g_StringLanType(szLan, "状态：系统被加锁（文件锁）", "Status:System has been locked (file lock)!");
                    m_csUpgradeStat.Format(szLan);
                    break;
                case 10:
                    g_StringLanType(szLan, "状态：备份区域异常", "Status:Backup regional anomaly!");
                    m_csUpgradeStat.Format(szLan);
                    break;
                case 11:
                    g_StringLanType(szLan, "状态：系统卡满", "Status:System card is full!");
                    m_csUpgradeStat.Format(szLan);
                    break;
                case 12:
                    g_StringLanType(szLan, "状态：重连升级失败（无效的SessionID）", "Status:Reconnect failed(Invalid SessionID)!");
                    m_csUpgradeStat.Format(szLan);
                    break;
                case 13:
                    g_StringLanType(szLan, "状态：服务正忙", "Status:Server is Busy!");
                    m_csUpgradeStat.Format(szLan);
                    break;
                case 14:
                    g_StringLanType(szLan, "状态：系统部分节点离线", "Status:System Node Is Offline!");
                    m_csUpgradeStat.Format(szLan);
                    break;
                case 15:
                    g_StringLanType(szLan, "状态：升级程序执行出错", "Status:Upgrade Prog Error!");
                    m_csUpgradeStat.Format(szLan);
                    break;
                case 16:
                    g_StringLanType(szLan, "状态：没有设备（LED控制器没有连接接收卡和多功能卡）", "Status:No Device!");
                    m_csUpgradeStat.Format(szLan);
                    break;
                case 17:
                    g_StringLanType(szLan, "状态：没有找到升级文件", "Status:No Find File!");
                    m_csUpgradeStat.Format(szLan);
                    break;
                case 18:
                    g_StringLanType(szLan, "状态：升级文件数据不兼容", "Status:Upgrade File Data Error!");
                    m_csUpgradeStat.Format(szLan);
                    break;
                case 19:
                    g_StringLanType(szLan, "状态：内存不足", "Status:No Memory!");
                    m_csUpgradeStat.Format(szLan);
                    break;
                case 20:
                    g_StringLanType(szLan, "状态：与服务器连接失败", "Status:Link Server Fail!");
                    m_csUpgradeStat.Format(szLan);
                    break;
                case 21:
                    g_StringLanType(szLan, "状态：oemCode 不匹配", "Status:OemCode Match!");
                    m_csUpgradeStat.Format(szLan);
                    break;
                case 22:
                    g_StringLanType(szLan, "状态：flash不足", "Status:Flash No Enough!");
                    m_csUpgradeStat.Format(szLan);
                    break;
                case 23:
                    g_StringLanType(szLan, "状态：RAM不足", "Status:RAM No Enough!");
                    m_csUpgradeStat.Format(szLan);
                    break;
                case 24:
                    g_StringLanType(szLan, "状态：DSP RAM不足", "Status:DSP RAM No Enough!");
                    m_csUpgradeStat.Format(szLan);
                    break;
                case 25:
                    g_StringLanType(szLan, "状态：升级包引擎版本不匹配", "Status:Upgrade Engine Version Mismatch!");
                    m_csUpgradeStat.Format(szLan);
                    break;
				default: 
					break;
				}
				UpdateData(FALSE);
                StopUpgrade();
			}
		}		
	}
    else if (nIDEvent == UPGRADE_TEST_TIMER)
    {
        if (m_bUpgrade)
        {
            StopUpgrade();
        }
        OnBnClickedBtnUpgrade();
        g_pMainDlg->AddLog(m_iDeviceIndex, OPERATION_SUCC_T, "Start UpGrade");
    }
	CDialog::OnTimer(nIDEvent);
}

/*********************************************************
  Function:	OnBtnSetEnviro
  Desc:		set the environment of the network
  Input:	none
  Output:	none
  Return:	none
**********************************************************/
void CDlgUpgrade::OnBtnSetEnviro() 
{
	// TODO: Add your control notification handler code here
	UpdateData(TRUE);
	char szLan[128] = {0};

	if (!NET_DVR_SetNetworkEnvironment(m_comboEnvironment.GetCurSel()))
	{
		g_pMainDlg->AddLog(m_iDeviceIndex, OPERATION_FAIL_T, "NET_DVR_SetNetworkEnvironment[%d]", m_comboEnvironment.GetCurSel());
		g_StringLanType(szLan, "设置网络环境", "Set up the network environment!");
		AfxMessageBox(szLan);
	}
	else
	{
		g_pMainDlg->AddLog(m_iDeviceIndex, OPERATION_SUCC_T, "NET_DVR_SetNetworkEnvironment[%d]", m_comboEnvironment.GetCurSel());
	}
	
}

void CDlgUpgrade::OnSelchangeComboUpgradeType() 
{
    char szLan[64] = {0};
    if (m_comboUpgradeType.GetCurSel() == 2)
    {
		g_StringLanType(szLan, "通道", "Chan");
		GetDlgItem(IDC_STATIC_CHAN)->SetWindowText(szLan);
        GetDlgItem(IDC_STATIC_CHAN)->ShowWindow(SW_SHOW);
        m_comboChan.ShowWindow(SW_SHOW);

		m_comboChan.ResetContent();
		char szLan[128] = {0};
		for (int i = 0; i < g_struDeviceInfo[m_iDeviceIndex].iDeviceChanNum; i++)
		{
			sprintf(szLan, "Chan %d", i + 1);
			m_comboChan.AddString(szLan);
		}
    }
    else
    {
        GetDlgItem(IDC_STATIC_CHAN)->ShowWindow(SW_HIDE);
        m_comboChan.ShowWindow(SW_HIDE);
    }
    if (m_comboUpgradeType.GetCurSel() == 3)
    {
        GetDlgItem(IDC_STATIC_ACS_NO)->ShowWindow(SW_SHOW);
        GetDlgItem(IDC_EDIT_ACS_NO)->ShowWindow(SW_SHOW);
        GetDlgItem(IDC_BTN_SELECT_DEV)->ShowWindow(SW_SHOW);
        GetDlgItem(IDC_BTN_KEEP_UPGRATE)->ShowWindow(SW_SHOW);
        GetDlgItem(IDC_BTN_STOP_KEEP_UPGRATE)->ShowWindow(SW_SHOW);
    }
    else
    {
        GetDlgItem(IDC_STATIC_ACS_NO)->ShowWindow(SW_HIDE);
        GetDlgItem(IDC_EDIT_ACS_NO)->ShowWindow(SW_HIDE);
        GetDlgItem(IDC_BTN_SELECT_DEV)->ShowWindow(SW_HIDE);
        GetDlgItem(IDC_BTN_KEEP_UPGRATE)->ShowWindow(SW_HIDE);
        GetDlgItem(IDC_BTN_STOP_KEEP_UPGRATE)->ShowWindow(SW_HIDE);
    }
    if (m_comboUpgradeType.GetCurSel() == 4)
    {
        g_StringLanType(szLan, "设备", "Dev");
        GetDlgItem(IDC_STATIC_CHAN)->SetWindowText(szLan);
        GetDlgItem(IDC_STATIC_CHAN)->ShowWindow(SW_SHOW);
        m_comboChan.ShowWindow(SW_SHOW);
        
        m_comboChan.ResetContent();        
        for (int i = 0; i < 32; i++)
        {
            sprintf(szLan, "Dev %d", i);
            m_comboChan.AddString(szLan);
        }
    }
    else
    {
        GetDlgItem(IDC_STATIC_CHAN)->ShowWindow(SW_HIDE);
        m_comboChan.ShowWindow(SW_HIDE);
    }
	if (m_comboUpgradeType.GetCurSel() == 5)
	{
		g_StringLanType(szLan, "类型", "Type");
        GetDlgItem(IDC_STATIC_CHAN)->SetWindowText(szLan);
		GetDlgItem(IDC_STATIC_TYPE)->ShowWindow(SW_SHOW);
		GetDlgItem(IDC_COMBO_CARD_TYPE)->ShowWindow(SW_SHOW);
	}
	else
	{
		GetDlgItem(IDC_STATIC_TYPE)->ShowWindow(SW_HIDE);
		GetDlgItem(IDC_COMBO_CARD_TYPE)->ShowWindow(SW_HIDE);
	}
}

void CDlgUpgrade::OnBtnGetupgradeinfo() 
{
	// TODO: Add your control notification handler code here
	//2013-06-17
	UpdateData(TRUE);
	if(m_csUpgradeFile.Compare(_T("")) == 0)
	{
		AfxMessageBox("文件路径为空!");
		return;
	}
	char szFileName[64] = {0};
	long lFileNameLen = 64;
	CString strFileName;
	CString strFilePath;
	char* szFilePath = new char[m_csUpgradeFile.GetLength()+1];
	memset(szFilePath, 0, sizeof(szFilePath));
	memcpy(szFilePath, m_csUpgradeFile, m_csUpgradeFile.GetLength()+1);
 	
// 	if(!NET_DVR_FindTargetFile(m_lServerID, m_lChannel, szFilePath, szFileName, lFileNameLen))
// 	{
// 		delete []szFilePath;
// 		szFilePath = NULL;
// 		DWORD dwRet = NET_DVR_GetLastError();
// 		if (dwRet == NET_DVR_DIR_ERROR)
// 		{
// 			AfxMessageBox("路径错误!");
// 			return;
// 		}
// 		if (dwRet == NET_DVR_NO_CURRENT_UPDATEFILE)
// 		{
// 			AfxMessageBox("没有匹配文件!");
// 			return;
// 		}
// 		return;
// 	}

	NET_DVR_FUZZY_UPGRADE struFuzzyUpgrade = {0};
	DWORD dwReturn = 0;
	BOOL bRet = NET_DVR_GetDVRConfig(m_lServerID, NET_DVR_GET_FUZZY_UPGRADE, m_lChannel, &struFuzzyUpgrade, sizeof(struFuzzyUpgrade), &dwReturn);
	if (!bRet)
	{
		char szLan[128] = {0};
		g_StringLanType(szLan, "获取信息失败", "Get ParamInfo failed");
 		AfxMessageBox(szLan);
		return;
	}
	char chTargeName[260] = {0};
	int iRet = findTargetFile(szFilePath, struFuzzyUpgrade.sUpgradeInfo, chTargeName);
	if(iRet == 0)
	{
 		strFileName.Format(_T("%s"), chTargeName);
		m_csUpgradeFile.Format(_T("%s"), strFileName);
		delete []szFilePath;
		szFilePath = NULL;
	}
	delete []szFilePath;
	szFilePath = NULL;
	UpdateData(FALSE);
}

/******************************************
函数:	ConvertData
描述:	利用简单的异或进行数据变换，用于升级文件的打包和解包  
输入:	src - source data
		len - data length
输出:	dst - destination  data
返回值: HPR_OK-成功，HPR_ERROR-失败
******************************************/
int CDlgUpgrade::ConvertData(const char *src, char *dst, int nLen)
{
    /* 固定的幻数，用于异或变换 */
    BYTE byMagic[16] = {0xba, 0xcd, 0xbc, 0xfe, 0xd6, 0xca, 0xdd, 0xd3,
		0xba, 0xb9, 0xa3, 0xab, 0xbf, 0xcb, 0xb5, 0xbe};
    int i, j;
    int nMagiclen, nStartMagic;
	
	//判断参数有效性
    if(src == NULL || dst == NULL)
    {
        return -1;
    }
	
    nMagiclen = sizeof(byMagic);
	//lint --e{440}
    for(i = 0, nStartMagic = 0; i<nLen; nStartMagic = (nStartMagic + 1) % nMagiclen)
    {
        //用startmagic控制每次内循环magic的起始位置
        for(j = 0; (j < nMagiclen) && (i < nLen); j++, i++)
        {
			// 进行异或变换
            //“(char)”类型强制转换不会有问题，因为是在做异或操作
            *dst++ = *src++ ^ (char)byMagic[(nStartMagic + j) % nMagiclen];   
        }
    }
    return 0;
}
#define UPDATE_FILE_FLAG_SIZE  18
#define UPDATE_FILE_HEAD_SIZE  64

/*************************************************
Function: findTargetFile 
Description: 查找目标文件
Input:     szFilePath: 文件夹路径
szFileFlag: 匹配标识
Output: szTargetFileName: 目标文件 
Return: 0成功,-1失败
*************************************************/
int CDlgUpgrade::findTargetFile(const char* szFilePath, const char* szFileFlag, char* szTargetFileName)
{
#if defined(_WIN32) || defined(_WIN64)
	char szFind[MAX_PATH] = {0};
	char szFile[MAX_PATH] = {0};
	WIN32_FIND_DATA FindFileData;
	strcpy(szFind, szFilePath);
    strcat(szFind, "\\*.*");
	HANDLE hFind = ::FindFirstFileA(szFind, &FindFileData);
    if (INVALID_HANDLE_VALUE == hFind)
	{
		FindClose(hFind);
		return -1;
	}
	while(TRUE)
    {
        if (FindFileData.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY)
        {
            if(FindFileData.cFileName[0] != '.') //存在子文件夹
            {
                strcpy(szFile, szFilePath);
                strcat(szFile, "\\");
                strcat(szFile, FindFileData.cFileName);
                if (findTargetFile(szFile, szFileFlag, szTargetFileName) == 0)
                {
					return 0;
                }
            }
        }
        else
        {      //deal with FindFileData.cFileName
			strcpy(szFile,szFilePath);
			strcat(szFile, "\\");
			strcat(szFile,FindFileData.cFileName);
			
			HANDLE hFile = ::CreateFileA(szFile, GENERIC_READ, 0, NULL, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, NULL);
			if (INVALID_HANDLE_VALUE != hFind)
			{
				if (::SetFilePointer(hFile, 0, 0, FILE_BEGIN) != HFILE_ERROR)
				{
					char szReadBuf[UPDATE_FILE_HEAD_SIZE+1] = {0};
					DWORD dwRealReadNum = 0;
					if (ReadFile(hFile, szReadBuf, UPDATE_FILE_HEAD_SIZE, &dwRealReadNum, NULL))
					{
						if (dwRealReadNum == UPDATE_FILE_HEAD_SIZE)
						{
							char szDecodeRes[UPDATE_FILE_HEAD_SIZE+1] = {0};
							char szDecodeFlag[UPDATE_FILE_FLAG_SIZE+1] = {0};
							//解码文件头信息
							ConvertData(szReadBuf, szDecodeRes, UPDATE_FILE_HEAD_SIZE);
							//从文件头中取出FLAG
							for (int i = 0; i < UPDATE_FILE_FLAG_SIZE; i++)
							{
								szDecodeFlag[i] = szDecodeRes[i+44];
							}
						//	DebugString("Flag:%s", szDecodeFlag);
							if (strcmp(szDecodeFlag, szFileFlag) == 0)  //找到匹配文件，不在继续搜索
							{
								strcpy(szTargetFileName, szFile);
								CloseHandle(hFile);
								FindClose(hFind);
								return 0;
							}
						}
					}
				}
			}
			CloseHandle(hFile);
			
        }
		if(!FindNextFile(hFind,&FindFileData)) //文件搜索结束
		{
			break;
		}
    }
    FindClose(hFind);
	return -1;
#else
	return -1;
#endif
}


void CDlgUpgrade::OnBnClickedBtnSelectDev()
{
    // TODO:  在此添加控件通知处理程序代码
    UpdateData(TRUE);
    CDlgUpgradeSelectDev dlg;
    dlg.DoModal();
    UpdateData(FALSE);
}


void CDlgUpgrade::OnBnClickedBtnKeepUpgrade()
{
    // TODO:  在此添加控件通知处理程序代码
    OnBnClickedBtnUpgrade();
    m_lpKeepUpgradeTimer = SetTimer(UPGRADE_TEST_TIMER, 10 * 60 * 1000, NULL);
}


void CDlgUpgrade::OnBnClickedBtnStopKeepUpgrade()
{
    // TODO:  在此添加控件通知处理程序代码
    if (m_lpKeepUpgradeTimer)
    {
        KillTimer(UPGRADE_TEST_TIMER);
        StopUpgrade();
    }
}

void CDlgUpgrade::StopUpgrade()
{
    m_bUpgrade = FALSE;
    GetDlgItem(IDC_BTN_UPGRADE)->EnableWindow(TRUE);
    GetDlgItem(IDC_BTN_UPGRADE_EXIT)->EnableWindow(TRUE);
    GetDlgItem(IDC_BTN_BROWSE_FILE)->EnableWindow(TRUE);
    if (!NET_DVR_CloseUpgradeHandle(m_lUpgradeHandle))
    {
        g_pMainDlg->AddLog(m_iDeviceIndex, OPERATION_FAIL_T, "NET_DVR_CloseUpgradeHandle");
    }
    GetDlgItem(IDC_STATIC_STEP)->ShowWindow(SW_HIDE);
    GetDlgItem(IDC_PROGRESS_STEP)->ShowWindow(SW_HIDE);
    m_lUpgradeHandle = -1;
}

bool CDlgUpgrade::IsSupPreValidate()
{
    //1.获取系统能力/ISAPI/System/capabilities，解析出updateFirmwarePreValidation.updateHeaderLength
    NET_DVR_XML_CONFIG_INPUT xmlInput = { 0 };
    NET_DVR_XML_CONFIG_OUTPUT xmlOutput = { 0 };

    xmlInput.dwSize = sizeof(NET_DVR_XML_CONFIG_INPUT);
    xmlOutput.dwSize = sizeof(NET_DVR_XML_CONFIG_OUTPUT);

    char *strUrl = "GET /ISAPI/System/capabilities\r\n";
    xmlInput.lpRequestUrl = strUrl;
    xmlInput.dwRequestUrlLen = strlen(strUrl);
    xmlInput.lpInBuffer = NULL;
    xmlInput.dwInBufferSize = 0;
    //xmlInput.dwRecvTimeOut = 1000;  // 1秒超时

    char *pOutBuf = new char[100 * 1024];
    memset(pOutBuf, 0, 10 * 1024);
    xmlOutput.lpOutBuffer = pOutBuf;
    xmlOutput.dwOutBufferSize = 100 * 1024;

    bool bRet = false;
    if (NET_DVR_STDXMLConfig(m_lServerID, &xmlInput, &xmlOutput))
    {
        //g_pMainDlg->AddLog(m_iDeviceIndex, OPERATION_SUCC_T, "NET_DVR_STDXMLConfig - Get capabilities success");

        CXmlBase xmlBase;
        if (!xmlBase.Parse(pOutBuf))
        {
            g_pMainDlg->AddLog(m_iDeviceIndex, OPERATION_FAIL_T, "Parse capabilities XML failed");
        }
        else if (xmlBase.FindElem("DeviceCap") && xmlBase.IntoElem())
        {

            if (xmlBase.FindElem("updateFirmwarePreValidation") && xmlBase.IntoElem())
            {
                bRet = true;
                if (xmlBase.FindElem("updateHeaderLength"))
                {
                    m_iPreValidateHeaderLength = atoi(xmlBase.GetData().c_str());
                }
                if (xmlBase.FindElem("languageType"))
                {
                    m_combolanguageType.ResetContent();
                    string strLangeTYpe = xmlBase.GetAttributeValue("opt");
                    int iIndex = 0;
                    CString strTmp = strtok((char *)strLangeTYpe.c_str(), ",");
                    while (strTmp != _T(""))
                    {
                        strTmp.TrimLeft();
                        m_combolanguageType.InsertString(iIndex, strTmp);
                        iIndex++;

                        strTmp = strtok(NULL, ",");
                    }
                    m_combolanguageType.SetCurSel(0);

                }
                xmlBase.OutOfElem();
            }
            else
            {
                g_pMainDlg->AddLog(m_iDeviceIndex, OPERATION_FAIL_T, "No firmware update pre-validation capability found");
            }
        }
    }
    else
    {
        DWORD dwError = NET_DVR_GetLastError();
        CString strError;
        strError.Format("get update pre-validation cap failed, error code: %d", dwError);
        g_pMainDlg->AddLog(m_iDeviceIndex, OPERATION_FAIL_T, strError);
    }

    delete[] pOutBuf;
    pOutBuf = NULL;

    return bRet;

}

void CDlgUpgrade::OnBnClickedBtnPreValidate()
{
    UpdateData(TRUE);
    memset(m_byUpgradeToken, 0, sizeof(m_byUpgradeToken));
    if (m_csUpgradeFile.Compare(_T("")) == 0)
    {
        AfxMessageBox("文件路径为空!");
        return;
    }

    if (!postPreValidateReq())
    {
        return ;
    }
    m_progressUpgrade.ShowWindow(SW_SHOW);
    

    if (getPreValidateRsp())
    {
        GetDlgItem(IDC_CHK_FORCE_UPGRADE)->ShowWindow(SW_SHOW);
    }

    //TODO:删除
    /*CString a = "{ \"status\": \"confirm\", \"progress\": 100, \"results\": { \"upgradeToken\": \"123e4567-e89b-12d3-a456-426614174000\", \"confirmPrompt\": \"test\" } }";
    ParsePreValidationResult(a);*/
}


bool CDlgUpgrade::postPreValidateReq()
{
    // 2.下发本地升级预校验 PUT /ISAPI/System/updateFirmware/AddPreValidation?format=json
    // 构建JSON请求报文
    bool bRet = false;
    char szLan[128] = { 0 };
    cJSON* pRoot = cJSON_CreateObject();
    cJSON* pUpgradePacketPath = cJSON_CreateObject();

    cJSON* pFilePathType = cJSON_CreateString("multipart");
    cJSON* pFilePath = cJSON_CreateString("updateFileName"); 
    cJSON_AddItemToObject(pUpgradePacketPath, "filePathType", pFilePathType);
    cJSON_AddItemToObject(pUpgradePacketPath, "filePath", pFilePath);
    cJSON_AddItemToObject(pRoot, "upgradePacketPath", pUpgradePacketPath);


    CString strText;
    int nCurSel = m_combolanguageType.GetCurSel();
    if (nCurSel != CB_ERR)
    {
        m_combolanguageType.GetLBText(nCurSel, strText);
    }
    cJSON* pLanguageType = cJSON_CreateString(strText);
    cJSON_AddItemToObject(pRoot, "languageType", pLanguageType);

    //CString strJsonRequest;
    //strJsonRequest.Format(
    //    _T("{\r\n")
    //    _T("    \"upgradePacketPath\": {\r\n")
    //    _T("        \"filePathType\": \"multipart\",\r\n")
    //    _T("        \"filePath\": \"%s\"\r\n")
    //    _T("    },\r\n")
    //    _T("    \"languageType\": \"%s\"\r\n")
    //    _T("}"),
    //    "updateFileName", "English"
    //    );

    DWORD dwInputLen = ISAPI_DATA_LEN;
    char *szInParamBuf = new char[dwInputLen];
    szInParamBuf = cJSON_Print(pRoot);

    NET_DVR_XML_CONFIG_INPUT xmlInput = { 0 };
    NET_DVR_XML_CONFIG_OUTPUT xmlOutput = { 0 };

    xmlInput.dwSize = sizeof(NET_DVR_XML_CONFIG_INPUT);
    xmlOutput.dwSize = sizeof(NET_DVR_XML_CONFIG_OUTPUT);

    char *strUrl = "PUT /ISAPI/System/updateFirmware/AddPreValidation?format=json\r\n";
    xmlInput.lpRequestUrl = strUrl;
    xmlInput.dwRequestUrlLen = strlen(strUrl);

    NET_DVR_MIME_UNIT struUnit[2] = { 0 };
    int iNumofMime = 0;
    struUnit[iNumofMime].pContent = szInParamBuf;
    struUnit[iNumofMime].dwContentLen = strlen(szInParamBuf);
    memcpy(struUnit[iNumofMime].szContentType, _T("text/json"), strlen(_T("text/json")));
    memcpy(struUnit[iNumofMime].szName, _T("AddPreValidation"), strlen(_T("AddPreValidation")));
    memcpy(struUnit[iNumofMime].szFilename, _T(""), strlen(_T("")));
    iNumofMime += 1;


    BYTE* pHeaderData = new BYTE[m_iPreValidateHeaderLength];
    FILE *fUpgradeFile = fopen(m_csUpgradeFile, "rb");
    if (NULL == fUpgradeFile)
    {
        g_StringLanType(szLan, "打开文件失败或无此文件", "Open file failed or no this file");
        AfxMessageBox(szLan);
        return false;
    }

    UINT nBytesRead = fread(pHeaderData, 1, m_iPreValidateHeaderLength, fUpgradeFile);

    if (nBytesRead != m_iPreValidateHeaderLength)
    {
        g_StringLanType(szLan, "读取头数据失败", "Read header data failed");
        AfxMessageBox(szLan);
        delete[] pHeaderData;
        pHeaderData = NULL;
        fclose(fUpgradeFile);
        return false;
    }
    
    struUnit[iNumofMime].pContent = (char*)pHeaderData;
    struUnit[iNumofMime].dwContentLen = m_iPreValidateHeaderLength;
    struUnit[iNumofMime].bySelfRead = 0;
    memcpy(struUnit[iNumofMime].szContentType, _T("application/octet-stream"), strlen(_T("application/octet-stream")));
    memcpy(struUnit[iNumofMime].szName, _T("updateFileName"), strlen(_T("updateFileName")));
    memcpy(struUnit[iNumofMime].szName, _T("updateFileName"), strlen(_T("updateFileName")));
    iNumofMime += 1;


    xmlInput.lpInBuffer = (char*)struUnit;
    xmlInput.dwInBufferSize = iNumofMime * sizeof(NET_DVR_MIME_UNIT);
    xmlInput.byNumOfMultiPart = iNumofMime;

    char *pOutBuf = new char[5 * 1024];
    memset(pOutBuf, 0, 5 * 1024);
    xmlOutput.lpOutBuffer = pOutBuf;
    xmlOutput.dwOutBufferSize = 5 * 1024;

    BOOL bResult = NET_DVR_STDXMLConfig(m_lServerID, &xmlInput, &xmlOutput);

    if (bResult)
    {
        cJSON* pRootResp = cJSON_Parse(pOutBuf);
        if (pRootResp != NULL)
        {
            cJSON *pStatus = cJSON_GetObjectItem(pRootResp, "statusString");
            if (strcmp(pStatus->valuestring, "OK") == 0)
            {
                bRet = true;
            }
            else
            {
                CString strError;
                strError.Format("Send pre-validation request failed: %s", pStatus->valuestring);
                g_pMainDlg->AddLog(m_iDeviceIndex, OPERATION_FAIL_T, strError);
            }
        }
        else
        {
            g_StringLanType(szLan, "设备返回内容有误，无法解析json报文!", "The returned json message is error.");
            AfxMessageBox(szLan);
        }

    }
    else
    {
        DWORD dwError = NET_DVR_GetLastError();
        CString strError;
        strError.Format("Send pre-validation request failed, error code: %d", dwError);
        g_pMainDlg->AddLog(m_iDeviceIndex, OPERATION_FAIL_T, strError);
    }

    if (pHeaderData != NULL)
    {
        delete[] pHeaderData;
        pHeaderData = NULL;
    }

    if (fUpgradeFile != NULL)
    {
        fclose(fUpgradeFile);
    }


    if (pRoot != NULL)
    {
        cJSON_Delete(pRoot);
    }

    if (szInParamBuf != NULL)
    {
        delete[] szInParamBuf;
        szInParamBuf = NULL;
    }
    if (pOutBuf != NULL)
    {
        delete[] pOutBuf;
        pOutBuf = NULL;
    }
    return bRet;
    
}
CDlgUpgrade::PreValidationResult CDlgUpgrade::ParsePreValidationResult(const char* pResponse)
{
    PreValidationResult result;
    result.status = PreValidationStatus::UNKNOWN;
    cJSON* pRoot = cJSON_Parse(pResponse);

    cJSON *pStatus = cJSON_GetObjectItem(pRoot, "status");
    if (pStatus != NULL)
    {
        if (strcmp(pStatus->valuestring, "verifying") == 0)
        {
            result.status = PreValidationStatus::VERIFYING;
        }
        else if (strcmp(pStatus->valuestring, "abnormal") == 0)
        {
            result.status = PreValidationStatus::ABNORMAL;
        }
        else if (strcmp(pStatus->valuestring, "confirm") == 0)
        {
            result.status = PreValidationStatus::CONFIRM;
        }
        else if (strcmp(pStatus->valuestring, "succ") == 0)
        {
            result.status = PreValidationStatus::SUCC;
        }
        else if (strcmp(pStatus->valuestring, "fail") == 0)
        {
            result.status = PreValidationStatus::FAIL;
        }

    }
    cJSON *pProgress = cJSON_GetObjectItem(pRoot, "progress");
    if (pProgress != NULL)
    {
        result.iProgress = pProgress->valueint;
    }

    //如果需要二次确认
    if (result.status == PreValidationStatus::CONFIRM)
    {
        cJSON *pResults = cJSON_GetObjectItem(pRoot, "results");
        if (pResults != NULL)
        {
            cJSON *pUpgradeToken = cJSON_GetObjectItem(pResults, "upgradeToken");
            if (pUpgradeToken != NULL)
            {
                result.strUpgradeToken = pUpgradeToken->valuestring;
            }

            cJSON *pConfirmPrompt = cJSON_GetObjectItem(pResults, "confirmPrompt");
            if (pConfirmPrompt != NULL)
            {
                result.strConfirmPrompt = pConfirmPrompt->valuestring;
            }
        }
    }
    return result;
}

bool CDlgUpgrade::getPreValidateRsp()
{
    //3.GET ISAPI/System/updateFirmware/GetPreValidationResults?format=json
    const int MAX_RETRY_COUNT = 60;  // 最大重试次数（约1分钟）
    const int QUERY_INTERVAL = 1000; // 查询间隔1秒
    for (int i = 0; i < MAX_RETRY_COUNT; i++)
    {
        // 等待间隔
        Sleep(QUERY_INTERVAL);

        // 发送GET查询请求
        NET_DVR_XML_CONFIG_INPUT xmlInput = { 0 };
        NET_DVR_XML_CONFIG_OUTPUT xmlOutput = { 0 };

        xmlInput.dwSize = sizeof(NET_DVR_XML_CONFIG_INPUT);
        xmlOutput.dwSize = sizeof(NET_DVR_XML_CONFIG_OUTPUT);

        char *strUrl = "GET /ISAPI/System/updateFirmware/GetPreValidationResults?format=json\r\n";
        xmlInput.lpRequestUrl = strUrl;
        xmlInput.dwRequestUrlLen = strlen(strUrl);
        xmlInput.lpInBuffer = NULL;
        xmlInput.dwInBufferSize = 0;
        xmlInput.dwRecvTimeOut = 3000;  // 3秒超时

        char *pOutBuf = new char[10 * 1024];
        memset(pOutBuf, 0, 10 * 1024);
        xmlOutput.lpOutBuffer = pOutBuf;
        xmlOutput.dwOutBufferSize = 10 * 1024;

        BOOL bResult = NET_DVR_STDXMLConfig(m_lServerID, &xmlInput, &xmlOutput);
        if (bResult)
        {
            // 解析查询结果
            PreValidationResult result = ParsePreValidationResult(pOutBuf);

            switch (result.status)
            {
            case PreValidationStatus::VERIFYING:
                if (result.iProgress > 0)
                {
                    m_progressUpgrade.SetPos(result.iProgress);
                }
                break;
            case PreValidationStatus::CONFIRM:
                // 校验完成，需要用户二次确认，显示确认按钮和提示语
                memcpy(m_byUpgradeToken, result.strUpgradeToken, strlen(result.strUpgradeToken));
                showUTF8Message(result.strConfirmPrompt, this);
                
                delete[] pOutBuf;
                return true;
            case PreValidationStatus::SUCC:
                AfxMessageBox("Pre-validation success, ready for upgrade!");
                delete[] pOutBuf;
                return true;

            case PreValidationStatus::FAIL:
                AfxMessageBox("Pre-validation failed!");
                delete[] pOutBuf;
                return false;

            case PreValidationStatus::ABNORMAL:
                AfxMessageBox("Pre-validation abnormal termination!");
                delete[] pOutBuf;
                return false;

            default:
                g_pMainDlg->AddLog(m_iDeviceIndex, OPERATION_FAIL_T, "Unknown pre-validation status");
                delete[] pOutBuf;
                return false;
            }
        }
        else
        {
            DWORD dwError = NET_DVR_GetLastError();
            CString strError;
            strError.Format("Query pre-validation result failed, error code: %d", dwError);
            g_pMainDlg->AddLog(m_iDeviceIndex, OPERATION_FAIL_T, strError);
        }
        delete[] pOutBuf;
    }

    // 超时
    g_pMainDlg->AddLog(m_iDeviceIndex, OPERATION_FAIL_T, "Pre-validation query timeout");
    return false;

}

// 直接使用Unicode版本的API显示，绕过MBCS限制
void CDlgUpgrade::showUTF8Message(const CString& strUtf8, CWnd* pParent) {

    CStringW wstrMessage = CA2W(strUtf8, CP_UTF8);
    ::MessageBoxW(pParent ? pParent->GetSafeHwnd() : NULL,
        wstrMessage, L"提示", MB_OK | MB_ICONINFORMATION);
}
