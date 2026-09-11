#pragma once


// DlgAlarmChannConfig 对话框
void CALLBACK OnAlarmCallback(LONG lCommand, NET_DVR_ALARMER *pAlarmer, char *pAlarmInfo, DWORD dwBufLen, void* pUser);

class DlgAlarmChannConfig : public CDialogEx
{
	DECLARE_DYNAMIC(DlgAlarmChannConfig)

public:
	DlgAlarmChannConfig(CWnd* pParent = NULL);   // 标准构造函数
	virtual ~DlgAlarmChannConfig();

// 对话框数据
	enum { IDD = IDD_DLG_ALARMCHAN_CONFIG };

protected:
	virtual void DoDataExchange(CDataExchange* pDX);    // DDX/DDV 支持

	DECLARE_MESSAGE_MAP()
public:
	virtual BOOL OnInitDialog();
	afx_msg void OnBnClickedOk();
	// 新增函数：刷新列表和更新编辑框
	void CheckDeviceSupport();
	void GetIPIDChannelRelation();
	void ProcessDeviceStatusChanged(char* szJsonData);
	void SetupAlarmSubscribe();
	LONG m_lAlarmHandle;
	int m_iDeviceIndex;
	CListCtrl m_listAlarmChan;
	CEdit m_editChangeInfo;
	BOOL m_bDeviceSupport;
};
