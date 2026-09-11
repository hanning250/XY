#pragma once
#include "ATLComTime.h"
#include "afxdtctl.h"
#include "afxcmn.h"
#include "atltime.h"
#include "cjson/cJSON.h"

// CDlgEventReconciliation 对话框
struct MissingRange { //EVENT_SEQ_RANGE
    int iStartID;
    int iEndID;
};

#define MAX_QUERY_DAYS         100 //此处需要根据业务处理,原因是如果天数过多，会存在多处回绕点,当前仅考虑一个回绕点
#define MAX_SEQ_PER_SECONDS    20
#define MAX_QUERY_SECONDS      MAX_QUERY_DAYS * 24 * 3600
//#define MAX_SEQ_GAP            MAX_QUERY_SECONDS * MAX_SEQ_PER_SECONDS

// 流水号缺失查询常量
#ifdef DEMO_LAN_CN
    const CString STATUS_NO_DATA = _T("无流水号文件");
    const CString STATUS_MISSING_DATA = _T("补录完成");
#else
    const CString STATUS_NO_DATA = _T("No Data");
    const CString STATUS_MISSING_DATA = _T("No Missing Data");
#endif
class CDlgEventReconciliation : public CDialogEx
{
	DECLARE_DYNAMIC(CDlgEventReconciliation)

public:
	CDlgEventReconciliation(CWnd* pParent = NULL);   // 标准构造函数
	virtual ~CDlgEventReconciliation();
    virtual void PostNcDestroy();

// 对话框数据
	enum { IDD = IDD_DLG_EVENT_RECONCILIATION };

protected:
	virtual void DoDataExchange(CDataExchange* pDX);    // DDX/DDV 支持
    virtual BOOL OnInitDialog();
    afx_msg void OnTimer(UINT_PTR nIDEvent);
	DECLARE_MESSAGE_MAP()
public:
    int m_iDeviceIndex;
    afx_msg void OnBnClickedBtnFindMissingSeq();
    afx_msg void OnBnClickedBtnEventRetransmission();

    afx_msg void OnBnClickedCheckChanEnabled();
    afx_msg void OnBnClickedBtnHiseventUpload();

    //事件对账
    CString m_szRetransmissionID;
    CString m_szEventSeqMissing;
    CString m_szEventSeqReceivedRate; //对账时,显示对账完成/对账总数
    CString m_szEventSeq;
    CTime m_ctEventDateStart;
    CTime m_ctEventDateStop;
    CTime m_ctEventTimeStart;
    CTime m_ctEventTimeStop;
    CString m_strEventSequenceDev;
    int m_ReconciliationMaximum;
    int m_iMissingNum;  //用于记录对账时,下发的丢失序号的个数，也即m_szEventSeq的流水号个数

    //历史事件补录
    CString m_szHisEventRetransmissionID;
    CTime m_ctHisEventDateStart;
    CTime m_ctHisEventDateStop;
    CTime m_ctHisEventTimeStart;
    CTime m_ctHisEventTimeStop;
    BOOL m_bChanEnabled;
    CListCtrl m_listChan;
    CString m_szHisEventUploadMode;
    CListCtrl m_listEventType;
    CString m_szHisEventUploadProgress;
    CString m_szHisEventTaskID;
    BOOL m_bHisEventUploading;

    

    //事件对账
    bool SearchEventReconciliation();



    // 检查文件日期是否在范围内
    BOOL IsFileDateInRange(const char* szFileName, time_t tStartTime, time_t tEndTime);
    // 从JSON文件加载序列号
    void LoadSequencesFromFile(const char* szFileName, time_t tStartTime, time_t tEndTime,
        int** ppSequences, int* piCount, int* piSize);
    // 格式化缺失序列号为 "1,\r\n5~6,\r\n8" 格式
    char* FormatMissingSequences(int* pSequences, int iCount);
    // 结合设备返回的序号范围,进行过滤
    int FilterSequencesByRange(const CString& strSequences, int iMin, int iMax, CString& strResult);
    //根据重传ID查找
    int FindMissingSequences(const char* szRetransmissionID, time_t tStartTime, time_t tEndTime, CString& strResult);


    //从界面解析缺失的序列号
    void ParseEventSeq(const char* strSeq, int** pIDList, int* pListSize, MissingRange** ppRanges, int* pRangeCount);
    int CalculateEventCount(const CString& strSeq);
    cJSON* FormatReconciliationJson();

    // 将有序的整数数组压缩为 "1~3, 5, 8~10" 格式
    char* FormatSequenceRanges(int* pSequences, int iCount);
    //自动刷新功能（根据对账时的流水号，从最近一天的文件中找是否含有这个流水号，有就说明已经上传了）
    void FilterExistingSequences();

    //历史事件补录
    void UpdateChanStatus();
    void CheckSubscribeEventCapAbility();
    void GetHistoryEventTypes();
    bool StartHistoryEventUpload();
    bool CancelHistoryEventUpload();
    void GetHistoryEventUploadProgress();
    CString FormatISOTime(const CTime& date, const CTime& time);
    void SplitString(const CString& str, const CString& delimiter, CStringArray& result);

    afx_msg void OnBnClickedBtnFindMissingSeqDev();
    afx_msg void OnBnClickedCheckAutoRefresh();
    BOOL m_bAutoRefresh;
    CString m_szEventSeqMissingNum;
};
