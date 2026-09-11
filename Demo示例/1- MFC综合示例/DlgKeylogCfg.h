#pragma once


// CDlgKeylogCfg 对话框

class CDlgKeylogCfg : public CDialog
{
    DECLARE_DYNAMIC(CDlgKeylogCfg)

public:
    CDlgKeylogCfg(CWnd* pParent = NULL);   // 标准构造函数
    virtual ~CDlgKeylogCfg();

    // 对话框数据
    enum { IDD = IDD_DLG_OPENSSL_KEYLOG_CFG };
    CString	m_strFileName;

protected:
    virtual void DoDataExchange(CDataExchange* pDX);    // DDX/DDV 支持

    DECLARE_MESSAGE_MAP()
public:
    afx_msg void OnBnClickedButtonBrowseFile();
    afx_msg void OnBnClickedKeylogCfg();
    afx_msg void OnBnClickedCancel2();
};
