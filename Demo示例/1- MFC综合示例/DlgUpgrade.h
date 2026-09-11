#pragma once
#include "afxwin.h"


// CDlgUpgrade dialog
//update operation
class CDlgUpgrade : public CDialog
{
	DECLARE_DYNAMIC(CDlgUpgrade)

public:
	CDlgUpgrade(CWnd* pParent = NULL);   // standard constructor
	virtual ~CDlgUpgrade();

// Dialog Data

public:
	//{{AFX_DATA(CDlgUpgrade)
	enum { IDD = IDD_DLG_UPGRADE };
	CProgressCtrl	m_progressSub;
	CComboBox	m_comboChan;
	CComboBox	m_comboUpgradeType;
	CComboBox	m_comboEnvironment;
	CComboBox	m_comboCardType;
    CComboBox	m_comboAuxDev;
	CProgressCtrl	m_progressUpgrade;
	CString m_csUpgradeFile;
    CString m_csUpgradeURL;
	CString m_csUpgradeStat;
	CString	m_csUpgradeStep;
	BOOL	m_bFuzzyUpgrade;
    CString m_csUnitID;
    BOOL	m_bForceUpgrade;
	//}}AFX_DATA
	
	//{{AFX_VIRTUAL(CDlgUpgrade)
protected:
	virtual void DoDataExchange(CDataExchange* pDX);    // DDX/DDV support
	//}}AFX_VIRTUAL
protected:
	// Generated message map functions
	//{{AFX_MSG(CDlgUpgrade)
	virtual BOOL OnInitDialog();
	afx_msg void OnBnClickedBtnBrowseFile();
	afx_msg void OnBnClickedBtnUpgrade();
	afx_msg void OnBnClickedBtnUpgradeExit();
#if (_MSC_VER >= 1500)	//vs2008
    afx_msg void OnTimer(UINT_PTR nIDEvent);
#else
    afx_msg void OnTimer(UINT nIDEvent);
#endif
	afx_msg void OnBtnSetEnviro();
	afx_msg void OnSelchangeComboUpgradeType();
	afx_msg void OnBtnGetupgradeinfo();
	//}}AFX_MSG
	
	DECLARE_MESSAGE_MAP()
		
public:
	LONG m_lUpgradeHandle;
	
	LONG	m_lServerID;
	LONG    m_lChannel;
	UINT	m_lpUpgradeTimer;
	BOOL	m_bUpgrade;
	int		m_iDeviceIndex;
    BYTE    m_byUpgradeToken[36];
    int     m_iPreValidateHeaderLength;   //代表升级包校验头长度，单位：字节
    BOOL    m_bNeedForceUpgrade;
	int  findTargetFile(const char* szFilePath, const char* szFileFlag, char* szTargetFileName);
	int  ConvertData(const char *src, char *dst, int nLen);
	CString F_GetDirectoryPath();
    DWORD m_dwAcsNo;
    afx_msg void OnBnClickedBtnSelectDev();
    afx_msg void OnBnClickedBtnKeepUpgrade();
    afx_msg void OnBnClickedBtnStopKeepUpgrade();
    void StopUpgrade();
    UINT	m_lpKeepUpgradeTimer;
    bool IsSupPreValidate();
    afx_msg void OnBnClickedBtnPreValidate();
    bool postPreValidateReq();  //下发预校验请求
    bool getPreValidateRsp();   //获取预校验结果
    void showUTF8Message(const CString& strUtf8, CWnd* pParent = NULL);

    enum class PreValidationStatus
    {
        UNKNOWN = 0,
        VERIFYING,  // verifying
        ABNORMAL,   // abnormal
        CONFIRM,    // confirm
        SUCC,       // succ
        FAIL        // fail
    };

    struct PreValidationResult
    {
        PreValidationStatus  status;
        int iProgress;
        CString strUpgradeToken;
        CString strConfirmPrompt;
    };
    PreValidationResult ParsePreValidationResult(const char* pResponse);  //解析预校验结果
    CComboBox m_combolanguageType;
};
