// DlgKeylogCfg.cpp : 实现文件
//

#include "stdafx.h"
#include "ClientDemo.h"
#include "DlgKeylogCfg.h"
#include "afxdialogex.h"


// CDlgKeylogCfg 对话框

IMPLEMENT_DYNAMIC(CDlgKeylogCfg, CDialog)

CDlgKeylogCfg::CDlgKeylogCfg(CWnd* pParent /*=NULL*/)
    : CDialog(CDlgKeylogCfg::IDD, pParent)
{
    m_strFileName = _T("");
}

CDlgKeylogCfg::~CDlgKeylogCfg()
{
}

void CDlgKeylogCfg::DoDataExchange(CDataExchange* pDX)
{
	CDialog::DoDataExchange(pDX);
    DDX_Text(pDX, IDC_EDIT_FILENAME, m_strFileName);
}


BEGIN_MESSAGE_MAP(CDlgKeylogCfg, CDialog)
    ON_BN_CLICKED(IDC_BUTTON_BROWSE_FILE, &CDlgKeylogCfg::OnBnClickedButtonBrowseFile)
    ON_BN_CLICKED(ID_KEYLOG_CFG, &CDlgKeylogCfg::OnBnClickedKeylogCfg)
    ON_BN_CLICKED(IDCANCEL2, &CDlgKeylogCfg::OnBnClickedCancel2)
END_MESSAGE_MAP()


// CDlgKeylogCfg 消息处理程序


void CDlgKeylogCfg::OnBnClickedButtonBrowseFile()
{
    static char szFilter[] = "All File(*.*)|*.*||";
    CFileDialog dlg(TRUE, "*.*", NULL, OFN_HIDEREADONLY | OFN_OVERWRITEPROMPT, szFilter);
    if (dlg.DoModal() == IDOK)
    {
        m_strFileName = dlg.GetPathName();

        UpdateData(FALSE);
    }
}


void CDlgKeylogCfg::OnBnClickedKeylogCfg()
{
    UpdateData(TRUE);
    char szFileName[MAX_PATH];
    strcpy(szFileName, m_strFileName);
    if (NET_DVR_SetSDKLocalCfg((NET_SDK_LOCAL_CFG_TYPE)27, szFileName))
    {
        g_pMainDlg->AddLog(0, OPERATION_SUCC_T, "NET_DVR_SetSDKLocalCfg");
        CDialog::OnCancel();
    }
    else
    {
        g_pMainDlg->AddLog(0, OPERATION_FAIL_T, "NET_DVR_SetSDKLocalCfg");
    }
}


void CDlgKeylogCfg::OnBnClickedCancel2()
{
    CDialog::OnCancel();
}
