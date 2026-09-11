// DlgEventReconciliation.cpp : 实现文件
//

#include "stdafx.h"
#include "afxdialogex.h"
#include "ClientDemo.h"
#include "DlgEventReconciliation.h"

#define HIS_EVENT_UPLOAD_TIMER 1001
#define FIND_MISSING_SEQ_TIMER 1002

// CDlgEventReconciliation 对话框

IMPLEMENT_DYNAMIC(CDlgEventReconciliation, CDialogEx)

CDlgEventReconciliation::CDlgEventReconciliation(CWnd* pParent /*=NULL*/)
	: CDialogEx(CDlgEventReconciliation::IDD, pParent)
    , m_iDeviceIndex(-1)
    , m_ctHisEventDateStart(0)
    , m_ctHisEventDateStop(0)
    , m_ctHisEventTimeStart(0)
    , m_ctHisEventTimeStop(0)
    , m_szHisEventUploadMode(_T(""))
    , m_szHisEventRetransmissionID(_T(""))
    , m_szHisEventUploadProgress(_T(""))
    , m_bChanEnabled(FALSE)
    , m_bHisEventUploading(FALSE)
    , m_szRetransmissionID(_T(""))
    , m_szEventSeqMissing(_T(""))
    , m_szEventSeq(_T(""))
    , m_ctEventDateStart(0)
    , m_ctEventDateStop(0)
    , m_ctEventTimeStart(0)
    , m_ctEventTimeStop(0)
    , m_strEventSequenceDev(_T(""))
    , m_ReconciliationMaximum(5000)
    , m_szEventSeqReceivedRate(_T(""))
    , m_bAutoRefresh(FALSE)
    , m_iMissingNum(0)
    , m_szEventSeqMissingNum(_T(""))
{

}

CDlgEventReconciliation::~CDlgEventReconciliation()
{
}

void CDlgEventReconciliation::PostNcDestroy()
{
    // 对话框关闭时清理资源
    CDialogEx::PostNcDestroy();
}

void CDlgEventReconciliation::DoDataExchange(CDataExchange* pDX)
{
    CDialogEx::DoDataExchange(pDX);

    DDX_Text(pDX, IDC_EDIT_RETRANSMISSION_ID, m_szRetransmissionID);
    DDX_Text(pDX, IDC_EDIT_EVENT_SEQUENCE_MISSING_NUM, m_szEventSeqMissingNum);
    DDX_Text(pDX, IDC_EDIT_EVENT_SEQUENCE_MISSING, m_szEventSeqMissing);
    DDX_Text(pDX, IDC_EDIT_EVENT_SEQUENCE, m_szEventSeq);

    DDX_Text(pDX, IDC_EDIT_HISEVNET_UPLOAD_RETRANS_ID, m_szHisEventRetransmissionID);
    DDX_DateTimeCtrl(pDX, IDC_DATE_HISEVENT_START, m_ctHisEventDateStart);
    DDX_DateTimeCtrl(pDX, IDC_DATE_HISEVENT_STOP, m_ctHisEventDateStop);
    DDX_DateTimeCtrl(pDX, IDC_TIME_HISEVENT_START, m_ctHisEventTimeStart);
    DDX_DateTimeCtrl(pDX, IDC_TIME_HISEVENT_STOP, m_ctHisEventTimeStop);
    DDX_Check(pDX, IDC_CHECK_CHAN_ENABLED, m_bChanEnabled);
    DDX_Control(pDX, IDC_LIST_CHANLIST, m_listChan);
    DDX_CBString(pDX, IDC_COMBO_HISEVENT_UPLOAD_MODE, m_szHisEventUploadMode);
    DDX_Control(pDX, IDC_LIST_HISEVENT_TYPE, m_listEventType);
    DDX_Text(pDX, IDC_EDIT_HISEVNET_UPLOAD_PROGRESS, m_szHisEventUploadProgress);


    DDX_DateTimeCtrl(pDX, IDC_DATE_EVENT_START, m_ctEventDateStart);
    DDX_DateTimeCtrl(pDX, IDC_DATE_EVENT_STOP, m_ctEventDateStop);
    DDX_DateTimeCtrl(pDX, IDC_TIME_EVENT_START, m_ctEventTimeStart);
    DDX_DateTimeCtrl(pDX, IDC_TIME_EVENT_STOP, m_ctEventTimeStop);
    DDX_Text(pDX, IDC_EDIT_EVENT_SEQUENCE_DEV, m_strEventSequenceDev);
    DDX_Text(pDX, IDC_EDIT_EVENT_SEQUENCE_RATE, m_szEventSeqReceivedRate);
    DDX_Check(pDX, IDC_CHECK_AUTO_REFRESH, m_bAutoRefresh);
}

BEGIN_MESSAGE_MAP(CDlgEventReconciliation, CDialogEx)
    ON_BN_CLICKED(IDC_CHECK_CHAN_ENABLED, &CDlgEventReconciliation::OnBnClickedCheckChanEnabled)
    ON_WM_TIMER()
    ON_BN_CLICKED(IDC_BTN_HISEVENT_UPLOAD, &CDlgEventReconciliation::OnBnClickedBtnHiseventUpload)
    ON_BN_CLICKED(ID_BTN_FIND_MISSING_SEQ, &CDlgEventReconciliation::OnBnClickedBtnFindMissingSeq)
    ON_BN_CLICKED(ID_BTN_EVENT_RETRANSMISSION, &CDlgEventReconciliation::OnBnClickedBtnEventRetransmission)
    ON_BN_CLICKED(ID_BTN_FIND_MISSING_SEQ_DEV, &CDlgEventReconciliation::OnBnClickedBtnFindMissingSeqDev)
    ON_BN_CLICKED(IDC_CHECK_AUTO_REFRESH, &CDlgEventReconciliation::OnBnClickedCheckAutoRefresh)
END_MESSAGE_MAP()

BOOL CDlgEventReconciliation::OnInitDialog()
{
    CDialogEx::OnInitDialog();
    int iDeviceIndex = g_pMainDlg->GetCurDeviceIndex();
    if (iDeviceIndex == -1)
    {
        UpdateData(FALSE);
        return FALSE;
    }
    m_iDeviceIndex = iDeviceIndex;
    m_szRetransmissionID = g_struDeviceInfo[m_iDeviceIndex].szRetransmissionID;
    m_szHisEventRetransmissionID = g_struDeviceInfo[m_iDeviceIndex].szRetransmissionID;

    CTime timeCur = CTime::GetCurrentTime();
    CTime timeStart(timeCur.GetYear(), timeCur.GetMonth(), timeCur.GetDay(), 0, 0, 0);
    CTime timeStop(timeCur.GetYear(), timeCur.GetMonth(), timeCur.GetDay(), 23, 59, 59);
    m_ctEventDateStart = timeStart;
    m_ctEventTimeStart = timeStart;
    m_ctEventDateStop = timeStop;
    m_ctEventTimeStop = timeStop;

    m_ctHisEventDateStart = timeStart;
    m_ctHisEventTimeStart = timeStart;
    m_ctHisEventDateStop = timeStop;
    m_ctHisEventTimeStop = timeStop;



    m_listChan.SetExtendedStyle(m_listChan.GetExtendedStyle() | LVS_EX_CHECKBOXES);
    UpdateChanStatus();
    GetDlgItem(IDC_LIST_CHANLIST)->EnableWindow(FALSE);
    CComboBox* pCombo = (CComboBox*)GetDlgItem(IDC_COMBO_HISEVENT_UPLOAD_MODE);
    if (pCombo != NULL)
    {
        pCombo->SetCurSel(0); // 设置默认选中第一项
    }

    GetDlgItem(ID_BTN_EVENT_RETRANSMISSION)->EnableWindow(FALSE);
    GetDlgItem(ID_BTN_FIND_MISSING_SEQ_DEV)->EnableWindow(TRUE);
    GetDlgItem(IDC_BTN_HISEVENT_UPLOAD)->EnableWindow(FALSE);
    m_listEventType.SetExtendedStyle(m_listEventType.GetExtendedStyle() | LVS_EX_CHECKBOXES);
    m_listEventType.SetColumnWidth(0, LVSCW_AUTOSIZE);
    CheckSubscribeEventCapAbility();

    UpdateData(FALSE);
    return TRUE;
}

void CDlgEventReconciliation::OnTimer(UINT_PTR nIDEvent)
{
    if (nIDEvent == HIS_EVENT_UPLOAD_TIMER)
    {
        GetHistoryEventUploadProgress();
    }
    if (nIDEvent == FIND_MISSING_SEQ_TIMER)
    {

        FilterExistingSequences();
    }

    CDialogEx::OnTimer(nIDEvent);
}

void CDlgEventReconciliation::CheckSubscribeEventCapAbility()
{
    // 1. 查询是否支持历史事件补录功能
    NET_DVR_XML_CONFIG_INPUT  xmlConfigInput = { 0 };
    NET_DVR_XML_CONFIG_OUTPUT  xmlCongfigOutput = { 0 };
    xmlConfigInput.dwSize = sizeof(xmlConfigInput);
    xmlCongfigOutput.dwSize = sizeof(xmlCongfigOutput);

    char szUrl[256] = "GET /ISAPI/Event/notification/subscribeEventCap";
    xmlConfigInput.lpRequestUrl = szUrl;
    xmlConfigInput.dwRequestUrlLen = strlen(szUrl);

    DWORD dwOutputLen = 1024 * 1024;
    char *pOutBuf = new char[dwOutputLen];
    memset(pOutBuf, 0, dwOutputLen);

    xmlCongfigOutput.dwOutBufferSize = dwOutputLen;
    xmlCongfigOutput.lpOutBuffer = pOutBuf;

    if (!NET_DVR_STDXMLConfig(g_struDeviceInfo[m_iDeviceIndex].lLoginID, &xmlConfigInput, &xmlCongfigOutput))
    {
        char szLan[1024] = { 0 };
        g_StringLanType(szLan, "获取设备历史补录能力失败", "Get the ability of history event upload failed");
        AfxMessageBox(szLan);
        GetDlgItem(IDC_BTN_HISEVENT_UPLOAD)->EnableWindow(FALSE);
    }
    else
    {
        // 解析SubscribeEventCap参数
        CXmlBase xmlBase;
        xmlBase.Parse(pOutBuf);
        if (xmlBase.FindElem("SubscribeEventCap") && xmlBase.IntoElem())
        {
            BOOL bSupportCreate = FALSE;
            BOOL bSupportCancel = FALSE;
            BOOL bSupportStatus = FALSE;

            if (xmlBase.FindElem("isSupportEventReconciliation"))
            {
                CString strValue = xmlBase.GetData().c_str();
                if ("true" == strValue)
                {
                    GetDlgItem(ID_BTN_EVENT_RETRANSMISSION)->EnableWindow(TRUE);
                }
            }
            xmlBase.OutOfElem();
            xmlBase.IntoElem();
            if (xmlBase.FindElem("isSupportSearchEventReconciliation"))
            {
                CString strValue = xmlBase.GetData().c_str();
                if ("true" == strValue)
                {
                    GetDlgItem(ID_BTN_FIND_MISSING_SEQ_DEV)->EnableWindow(TRUE);
                }
            }
            xmlBase.OutOfElem();
            xmlBase.IntoElem();
            if (xmlBase.FindElem("supportReconciliationMaximum"))
            {
                CString strValue = xmlBase.GetData().c_str();
                m_ReconciliationMaximum = atoi(strValue);
            }

            xmlBase.OutOfElem();
            xmlBase.IntoElem();
            if (xmlBase.FindElem("isSupportCreateHistoryEventUploadTask"))
            {
                CString strValue = xmlBase.GetData().c_str();
                bSupportCreate = (strValue == "true");
            }

            if (xmlBase.FindElem("isSupportCancelHistoryEventUploadTask"))
            {
                CString strValue = xmlBase.GetData().c_str();
                bSupportCancel = (strValue == "true");
            }

            if (xmlBase.FindElem("isSupportGetHistoryEventUploadTaskStatus"))
            {
                CString strValue = xmlBase.GetData().c_str();
                bSupportStatus = (strValue == "true");
            }

            if (bSupportCreate && bSupportCancel && bSupportStatus)
            {
                GetDlgItem(IDC_BTN_HISEVENT_UPLOAD)->EnableWindow(TRUE);
                // 获取事件类型列表
                GetHistoryEventTypes();
            }
            else
            {
                GetDlgItem(IDC_BTN_HISEVENT_UPLOAD)->EnableWindow(FALSE);
                char szLan[1024] = { 0 };
                g_StringLanType(szLan, "设备不支持历史补录功能", "Device does not support history event upload");
                g_pMainDlg->AddLog(m_iDeviceIndex, OPERATION_FAIL_T, szLan);
            }
        }
        else
        {
            GetDlgItem(IDC_BTN_HISEVENT_UPLOAD)->EnableWindow(FALSE);
        }
    }

    delete[] pOutBuf;
    pOutBuf = NULL;
}


bool CDlgEventReconciliation::SearchEventReconciliation()
{
    // 构建JSON请求报文
    cJSON* pRoot = cJSON_CreateObject();

    // retransmissionID - 必需
    cJSON_AddStringToObject(pRoot, "retransmissionID", m_szHisEventRetransmissionID);

    // timeSpan - 必需
    cJSON* pTimeSpan = cJSON_CreateObject();

    // 格式化时间
    CString strStartTime = FormatISOTime(m_ctEventDateStart, m_ctEventTimeStart);
    CString strEndTime = FormatISOTime(m_ctEventDateStop, m_ctEventTimeStop);

    cJSON_AddStringToObject(pTimeSpan, "startTime", strStartTime);
    cJSON_AddStringToObject(pTimeSpan, "endTime", strEndTime);
    cJSON_AddItemToObject(pRoot, "timeSpan", pTimeSpan);

    // 发送请求
    char* szJsonRequest = cJSON_Print(pRoot);
    DWORD dwInputLen = strlen(szJsonRequest);

    NET_DVR_XML_CONFIG_INPUT xmlInput = { 0 };
    NET_DVR_XML_CONFIG_OUTPUT xmlOutput = { 0 };
    xmlInput.dwSize = sizeof(NET_DVR_XML_CONFIG_INPUT);
    xmlOutput.dwSize = sizeof(NET_DVR_XML_CONFIG_OUTPUT);

    char* strUrl = "POST /ISAPI/Event/notification/SearchEventReconciliation?format=json\r\n";
    xmlInput.lpRequestUrl = strUrl;
    xmlInput.dwRequestUrlLen = strlen(strUrl);

    xmlInput.lpInBuffer = szJsonRequest;
    xmlInput.dwInBufferSize = dwInputLen;

    DWORD dwOutputLen = 1024 * 1024;
    char* pOutBuf = new char[dwOutputLen];
    memset(pOutBuf, 0, dwOutputLen);
    xmlOutput.lpOutBuffer = pOutBuf;
    xmlOutput.dwOutBufferSize = dwOutputLen;

    BOOL bResult = NET_DVR_STDXMLConfig(g_struDeviceInfo[m_iDeviceIndex].lLoginID, &xmlInput, &xmlOutput);

    bool bRet = false;
    if (bResult)
    {
        CString strError;
        strError.Format(_T("NET_DVR_STDXMLConfig(%s)"), strUrl);
        cJSON* pRootResp = cJSON_Parse(pOutBuf);
        if (pRootResp != NULL)
        {
            cJSON* pStatus = cJSON_GetObjectItem(pRootResp, "statusString");
            if (pStatus != NULL && strcmp(pStatus->valuestring, "OK") != 0)
            {
                bRet = false;
                CString strError;
                strError.Format("NET_DVR_STDXMLConfig Search event reconciliation failed: %s", pStatus->valuestring);
                g_pMainDlg->AddLog(m_iDeviceIndex, OPERATION_FAIL_T, strError);
            }
            else
            {
                // 解析事件对账信息
                cJSON* pTotal = cJSON_GetObjectItem(pRootResp, "total");
                cJSON* pEventSequenceRange = cJSON_GetObjectItem(pRootResp, "eventSequenceRange");

                if (pTotal != NULL && pEventSequenceRange != NULL)
                {
                    int iTotal = pTotal->valueint;
                    cJSON* pStartSequenceID = cJSON_GetObjectItem(pEventSequenceRange, "startSequenceID");
                    cJSON* pEndSequenceID = cJSON_GetObjectItem(pEventSequenceRange, "endSequenceID");

                    if (pStartSequenceID != NULL && pEndSequenceID != NULL)
                    {
                        int iStartSequenceID = pStartSequenceID->valueint;
                        int iEndSequenceID = pEndSequenceID->valueint;

                        CString strResult;
                        strResult.Format("total: %d(%d~%d)", iTotal, iStartSequenceID, iEndSequenceID);
                        m_strEventSequenceDev = strResult;
                        UpdateData(FALSE);
                        bRet = true;
                    }
                }
            }
            cJSON_Delete(pRootResp);
        }
    }
    else
    {
        CString strError;
        strError.Format(_T("NET_DVR_STDXMLConfig(%s)"), strUrl);
        g_pMainDlg->AddLog(m_iDeviceIndex, OPERATION_FAIL_T, strError);
    }

    // 清理资源
    cJSON_Delete(pRoot);
    free(szJsonRequest);
    delete[] pOutBuf;

    return bRet;
}

void CDlgEventReconciliation::OnBnClickedBtnFindMissingSeqDev()
{
    // TODO:  在此添加控件通知处理程序代码
    UpdateData(TRUE);
    SearchEventReconciliation();
}


void CDlgEventReconciliation::OnBnClickedBtnFindMissingSeq()
{
    // TODO:  在此添加控件通知处理程序代码
    UpdateData(TRUE);
    CTime ctFullStart(m_ctEventDateStart.GetYear(), m_ctEventDateStart.GetMonth(), m_ctEventDateStart.GetDay(),
        m_ctEventTimeStart.GetHour(), m_ctEventTimeStart.GetMinute(), m_ctEventTimeStart.GetSecond());
    CTime ctFullStop(m_ctEventDateStop.GetYear(), m_ctEventDateStop.GetMonth(), m_ctEventDateStop.GetDay(),
        m_ctEventTimeStop.GetHour(), m_ctEventTimeStop.GetMinute(), m_ctEventTimeStop.GetSecond());

    time_t tStartTime = ctFullStart.GetTime();
    time_t tEndTime = ctFullStop.GetTime();

    CString strMissingSeq = "";
    int iMissingNum = FindMissingSequences(m_szRetransmissionID, tStartTime - MAX_QUERY_SECONDS, tEndTime + MAX_QUERY_SECONDS, strMissingSeq);

    if (strMissingSeq != "")
    {
        m_szEventSeqMissing = strMissingSeq;
        CString strTemp;
        m_szEventSeqMissingNum.Format(_T("%d"), iMissingNum);

        m_szEventSeq = strMissingSeq;
    }

    //解析设备端的范围根据设备端代码进行过滤
    if (!SearchEventReconciliation())
    {
        UpdateData(FALSE);
        return;
    }

    // 解析设备序列号范围
    int iDevMin = -1, iDevMax = -1;
    if (!m_strEventSequenceDev.IsEmpty())
    {
        CString strDev = m_strEventSequenceDev;
        if (strDev.Find("total:") != -1)
        {
            // 解析格式："total: %d(%d~%d)"
            sscanf_s(strDev, "total: %*d(%d~%d)", &iDevMin, &iDevMax);
        }
    }
    // 如果有设备范围信息，则过滤缺失序列号
    if (iDevMin != -1 && iDevMax != -1 && !m_szEventSeqMissing.IsEmpty() && m_szEventSeqMissing != STATUS_NO_DATA && m_szEventSeqMissing != STATUS_MISSING_DATA)
    {
        CString strFiltered = "";
        int iFilterMissingCount = FilterSequencesByRange(m_szEventSeqMissing, iDevMin, iDevMax, strFiltered);
        m_szEventSeq = strFiltered;   //TODO(HQH):
        m_szEventSeqMissing = strFiltered;
        m_szEventSeqMissingNum.Format(_T("%d"), iFilterMissingCount);

    }
    else
    {
        m_szEventSeq = m_szEventSeqMissing;
    }
    UpdateData(FALSE);
}
/** @fn void CAlarmAdvanceSetter::ParseEventSeq()
*  @brief 事件类型切换响应
*         将界面上读出的strSeq（1,3,5~9,10,12~15），将不连续的读到pIDList中，将连续的读到ppRanges中
*  @return void
*/
void CDlgEventReconciliation::ParseEventSeq(const char* strSeq, int** pIDList, int* pListSize, MissingRange** ppRanges, int* pRangeCount)
{
    if (strSeq == NULL || strcmp(strSeq, "") == 0)
    {
        *pIDList = NULL;
        *pListSize = 0;
        *ppRanges = NULL;
        *pRangeCount = 0;
        return;
    }

    char* pInput = strdup(strSeq);
    char* pToken = strtok(pInput, ",\r\n");
    int iNumbers[256] = { 0 };
    int iCount = 0;

    // 临时存储范围
    MissingRange struTempRanges[256] = { 0 };
    int iRangeCount = 0;

    // 解析所有数字和范围
    while (pToken != NULL) {
        char* pSeqRange = strchr(pToken, '~');
        if (pSeqRange) {
            // 处理范围格式（如 "5~8"）
            *pSeqRange = '\0';
            int iStartID = atoi(pToken);
            int iEndID = atoi(pSeqRange + 1);

            if (iStartID > 0 && iEndID >= iStartID) {
                struTempRanges[iRangeCount].iStartID = iStartID;
                struTempRanges[iRangeCount].iEndID = iEndID;
                iRangeCount++;
            }
        }
        else {
            // 处理单个数字
            int iNum = atoi(pToken);
            if (iNum > 0) {
                iNumbers[iCount++] = iNum;
            }
        }
        pToken = strtok(NULL, ",");
    }
    free(pInput);

    // 对单个数字去重并排序
    if (iCount > 0) {
        // 冒泡排序
        for (int i = 0; i < iCount - 1; i++) {
            for (int j = 0; j < iCount - i - 1; j++) {
                if (iNumbers[j] > iNumbers[j + 1]) {
                    int temp = iNumbers[j];
                    iNumbers[j] = iNumbers[j + 1];
                    iNumbers[j + 1] = temp;
                }
            }
        }

        // 去重
        int iUniqueCount = 0;
        for (int i = 0; i < iCount; i++) {
            if (i == 0 || iNumbers[i] != iNumbers[i - 1]) {
                iNumbers[iUniqueCount++] = iNumbers[i];
            }
        }
        *pIDList = (int*)malloc(iUniqueCount * sizeof(int));
        memcpy(*pIDList, iNumbers, iUniqueCount * sizeof(int));
        *pListSize = iUniqueCount;
    }
    else {
        *pIDList = NULL;
        *pListSize = 0;
    }

    // 处理范围数据
    if (iRangeCount > 0) {
        *ppRanges = (MissingRange*)malloc(iRangeCount * sizeof(MissingRange));
        memcpy(*ppRanges, struTempRanges, iRangeCount * sizeof(MissingRange));
        *pRangeCount = iRangeCount;
    }
    else {
        *ppRanges = NULL;
        *pRangeCount = 0;
    }
}

//根据流水号范围确认流水号的数量
int CDlgEventReconciliation::CalculateEventCount(const CString& strSeq)
{
    if (strSeq.IsEmpty())
    {
        return 0;
    }
    const char* szSeq = strSeq.GetString();

    // 轻量级解析，只计算数量不构建复杂结构
    char* pInput = strdup(szSeq);
    char* pToken = strtok(pInput, ",\r\n");
    int iTotalCount = 0;

    while (pToken != NULL) {
        char* pSeqRange = strchr(pToken, '~');
        if (pSeqRange) {
            *pSeqRange = '\0';
            int iStartID = atoi(pToken);
            int iEndID = atoi(pSeqRange + 1);
            if (iStartID > 0 && iEndID >= iStartID) {
                iTotalCount += (iEndID - iStartID + 1);
            }
        }
        else {
            int iNum = atoi(pToken);
            if (iNum > 0) iTotalCount++;
        }
        pToken = strtok(NULL, ",");
    }
    free(pInput);
    return iTotalCount;
}

cJSON* CDlgEventReconciliation::FormatReconciliationJson()
{
    int* pIDList = NULL;
    int iListSize = 0;
    int iRangeCount = 0;
    MissingRange* pRanges = NULL;

    ParseEventSeq(m_szEventSeq, &pIDList, &iListSize, &pRanges, &iRangeCount);

    cJSON* root = cJSON_CreateObject();
    cJSON_AddStringToObject(root, "retransmissionID", m_szRetransmissionID);

    cJSON* pEventReconciliationArray = cJSON_CreateArray();

    // eventSequenceIDList: 数组类型
    if (iListSize > 0) {
        cJSON* pSeqIDList = cJSON_CreateArray();
        for (int i = 0; i < iListSize; i++) {
            cJSON_AddItemToArray(pSeqIDList, cJSON_CreateNumber(pIDList[i]));
        }
        cJSON* pEventSequence = cJSON_CreateObject();
        cJSON_AddItemToObject(pEventSequence, "eventSequenceIDList", pSeqIDList);
        cJSON* pReconciliationItem = cJSON_CreateObject();
        cJSON_AddItemToObject(pReconciliationItem, "eventSequence", pEventSequence);
        cJSON_AddItemToArray(pEventReconciliationArray, pReconciliationItem);
    }

    for (int i = 0; i < iRangeCount; i++) {
        cJSON* pReconciliationItem = cJSON_CreateObject();
        cJSON* pEventSequence = cJSON_CreateObject();
        cJSON* pSeqRange = cJSON_CreateObject();

        cJSON_AddNumberToObject(pSeqRange, "startSequenceID", pRanges[i].iStartID);
        if (pRanges[i].iEndID > pRanges[i].iStartID) {
            cJSON_AddNumberToObject(pSeqRange, "endSequenceID", pRanges[i].iEndID);
        }

        cJSON_AddItemToObject(pEventSequence, "eventSequenceRange", pSeqRange);
        cJSON_AddItemToObject(pReconciliationItem, "eventSequence", pEventSequence);
        cJSON_AddItemToArray(pEventReconciliationArray, pReconciliationItem);
    }

    //说明:如果没有数据,代表不指定事件件流水号，需返回所有存储事件
    cJSON_AddItemToObject(root, "eventReconciliation", pEventReconciliationArray);

    // 清理资源
    if (pIDList) free(pIDList);
    if (pRanges) free(pRanges);

    return root;
}

void CDlgEventReconciliation::OnBnClickedBtnEventRetransmission()
{
    // TODO:  在此添加控件通知处理程序代码
    UpdateData(TRUE);
    int iTotalEventCount = CalculateEventCount(m_szEventSeq);
    
    if (iTotalEventCount > m_ReconciliationMaximum)
    {
        CString strMessage;
        strMessage.Format(_T("当前事件序号数量(%d)超过最大限制(%d)，请缩小范围分批处理。"),
            iTotalEventCount, m_ReconciliationMaximum);
        AfxMessageBox(strMessage);
        return;
    }
    //组装重传报文
    cJSON* pRoot = FormatReconciliationJson();
    if (pRoot == NULL)
    {
        AfxMessageBox("Event sequence is empty or format is incorrect!");
        return;
    }
    NET_DVR_XML_CONFIG_INPUT  xmlConfigInput = { 0 };
    xmlConfigInput.dwSize = sizeof(xmlConfigInput);
    char szUrl[256] = "";
    sprintf(szUrl, "POST /ISAPI/Event/notification/EventReconciliation?format=json");
    xmlConfigInput.lpRequestUrl = szUrl;
    xmlConfigInput.dwRequestUrlLen = strlen(szUrl);

    NET_DVR_XML_CONFIG_OUTPUT xmlOutput = { 0 };
    xmlOutput.dwSize = sizeof(NET_DVR_XML_CONFIG_OUTPUT);
    char *pOutBuf = new char[10 * 1024];
    memset(pOutBuf, 0, 10 * 1024);
    xmlOutput.lpOutBuffer = pOutBuf;
    xmlOutput.dwOutBufferSize = 10 * 1024;


    DWORD dwInputLen = 1024 * 2;
    char *szInParamBuf = new char[dwInputLen];
    szInParamBuf = cJSON_Print(pRoot);
    xmlConfigInput.lpInBuffer = szInParamBuf;
    xmlConfigInput.dwInBufferSize = strlen(szInParamBuf);


    if (!NET_DVR_STDXMLConfig(g_struDeviceInfo[m_iDeviceIndex].lLoginID, &xmlConfigInput, &xmlOutput))
    {
        CString strError;
        strError.Format(_T("NET_DVR_STDXMLConfig(%s)"), szUrl);
        g_pMainDlg->AddLog(-1, OPERATION_FAIL_T, strError);
    }
    else
    {
        m_iMissingNum = iTotalEventCount; //每次下发时，记录下对账的数量

        CString strError;
        strError.Format(_T("NET_DVR_STDXMLConfig(%s)"), szUrl);
        g_pMainDlg->AddLog(-1, OPERATION_SUCC_T, strError);
        AfxMessageBox((char*)xmlOutput.lpOutBuffer);
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
    UpdateData(FALSE);
}

// 辅助函数：比较MissingRange（用于qsort）
int CompareRanges(const void* a, const void* b) {
    const MissingRange* ra = (const MissingRange*)a;
    const MissingRange* rb = (const MissingRange*)b;
    // 防止减法溢出，使用比较运算符
    if (ra->iStartID < rb->iStartID) return -1;
    if (ra->iStartID > rb->iStartID) return 1;
    return 0;
}

// 辅助函数：比较整数（用于qsort）
int CompareInt(const void* a, const void* b)
{
    const int* pa = (const int*)a;
    const int* pb = (const int*)b;
    if (*pa < *pb) return -1;
    if (*pa > *pb) return 1;
    return 0;
}
//// 查询指定重传ID在时间范围内的缺失序列号
int CDlgEventReconciliation::FindMissingSequences(const char* szRetransmissionID, time_t tStartTime, time_t tEndTime, CString& strResult)
{
    char szDirPath[256];
    char szSearchPattern[256];
    WIN32_FIND_DATA findFileData;
    HANDLE hFind;

    // 构建目录路径和搜索模式
    sprintf(szDirPath, "%s\\%s", g_struLocalParam.chPictureSavePath, "retransmissonInfo");
    sprintf(szSearchPattern, "%s\\%s_*.json", szDirPath, szRetransmissionID);

    // 收集所有序列号
    int* pSequences = NULL;
    int iSequenceCount = 0;
    int iArraySize = 0;

    hFind = FindFirstFile(szSearchPattern, &findFileData);
    if (hFind != INVALID_HANDLE_VALUE)
    {
        do {
            if (!(findFileData.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY))
            {
                // 解析文件名中的日期
                char szFileName[256];
                sprintf(szFileName, "%s\\%s", szDirPath, findFileData.cFileName);

                // 检查文件日期是否在查询范围内
                if (IsFileDateInRange(szFileName, tStartTime, tEndTime))
                {
                    // 读取文件并提取序列号
                    LoadSequencesFromFile(szFileName, tStartTime, tEndTime, &pSequences, &iSequenceCount, &iArraySize);
                }
            }
        } while (FindNextFile(hFind, &findFileData));

        FindClose(hFind);
    }

    // 如果没有数据
    if (iSequenceCount == 0)
    {
        strResult = STATUS_NO_DATA;
        return 0;
    }

    // 排序序列号
    qsort(pSequences, iSequenceCount, sizeof(int), CompareInt);

    // 格式化缺失序列号
    char* szMissingSequences = FormatMissingSequences(pSequences, iSequenceCount);
    strResult = szMissingSequences;
    free(szMissingSequences);

    if (pSequences != NULL)
    {
        free(pSequences);
    }

    return iSequenceCount;
}

// 辅助函数：检查文件日期是否在范围内
BOOL CDlgEventReconciliation::IsFileDateInRange(const char* szFileName, time_t tStartTime, time_t tEndTime)
{
    // 从文件名中提取日期：534DEEC6-ED16-4A32-8FEB-35CD5C0C12C6_20241201.json
    const char* pszUnderscore = strrchr(szFileName, '_');
    if (pszUnderscore == NULL) return FALSE;

    char szDate[9];
    strncpy(szDate, pszUnderscore + 1, 8);
    szDate[8] = '\0';

    // 解析日期
    int year, month, day;
    sscanf(szDate, "%4d%2d%2d", &year, &month, &day);

    struct tm fileTm = { 0 };
    fileTm.tm_year = year - 1900;
    fileTm.tm_mon = month - 1;
    fileTm.tm_mday = day;
    time_t tFileDate = mktime(&fileTm);

    // 假设文件是24小时制的，每天0点创建
    long fileDuration = 24 * 60 * 60 * 1000L; // 24小时

    return ((tFileDate + fileDuration) >= tStartTime && tFileDate <= tEndTime);
}

// 辅助函数：从JSON文件加载序列号
void CDlgEventReconciliation::LoadSequencesFromFile(const char* szFileName, time_t tStartTime, time_t tEndTime,
    int** ppSequences, int* piCount, int* piSize)
{
    FILE* pFile = fopen(szFileName, "r");
    if (pFile == NULL) return;

    fseek(pFile, 0, SEEK_END);
    long lSize = ftell(pFile);
    fseek(pFile, 0, SEEK_SET);

    char* szFileContent = (char*)malloc(lSize + 1);
    if (szFileContent == NULL)
    {
        fclose(pFile);
        return;
    }

    fread(szFileContent, 1, lSize, pFile);
    szFileContent[lSize] = '\0';
    fclose(pFile);

    cJSON* pRootArray = cJSON_Parse(szFileContent);
    free(szFileContent);

    if (pRootArray == NULL)
    {
        return;
    }

    int iArraySize = cJSON_GetArraySize(pRootArray);
    for (int i = 0; i < iArraySize; i++)
    {
        cJSON* pItem = cJSON_GetArrayItem(pRootArray, i);
        if (pItem != NULL)
        {
            cJSON* pSequence = cJSON_GetObjectItem(pItem, "sequence");
            //cJSON* pTimestamp = cJSON_GetObjectItem(pItem, "timestamp");

            if (pSequence != NULL) //pTimestamp != NULL
            {
                //time_t tEventTime = (time_t)pTimestamp->valuedouble;

                //// 检查时间是否在范围内
                //if (tEventTime < tStartTime && tEventTime > tEndTime)
                //{
                //    continue;
                //}
                 //扩展数组
                if (*piCount >= *piSize)
                {
                    *piSize = (*piSize == 0) ? 100 : *piSize * 2;
                    *ppSequences = (int*)realloc(*ppSequences, *piSize * sizeof(int));
                }

                (*ppSequences)[*piCount] = pSequence->valueint;
                (*piCount)++;
            }
        }
    }

    cJSON_Delete(pRootArray);
}



// 辅助函数：已知存在的点 -> 推导中间缺失的区间，格式化缺失序列号为 "1,\r\n5~6,\r\n8" 格式
// 定义“接近 0"和“接近 INT_MAX"的阈值范围
// 对于 Demo，这个范围可以设大一点，比如 100 万(MAX_SEQ_GAP)
char* CDlgEventReconciliation::FormatMissingSequences(int* pSequences, int iCount)
{
    if (iCount == 0) return _strdup(STATUS_NO_DATA);
    if (iCount == 1) return _strdup(STATUS_MISSING_DATA);

    // 1. 必须排序
    qsort(pSequences, iCount, sizeof(int), CompareInt);

    // 临时数组存储缺失区间 (假设最多不会超过 iCount + 2 个区间)
    MissingRange* pRanges = (MissingRange*)malloc(sizeof(MissingRange) * (iCount + 5));
    int nRangeCount = 0;

    // 2. 判断是否回绕
    unsigned int span = (unsigned int)pSequences[iCount - 1] - (unsigned int)pSequences[0];
    bool bIsWrapped = (span > (unsigned int)(INT_MAX * 0.9)); // 90% 阈值
    //if (pSequences[0] < MAX_SEQ_GAP &&
    //    pSequences[iCount - 1] > (INT_MAX - MAX_SEQ_GAP))
    //{
    //    bIsWrapped = true;
    //}

    if (!bIsWrapped)
    {
        // --- 场景 A：普通线性序列 ---
        int nExpected = pSequences[0] + 1;
        for (int i = 1; i < iCount; i++)
        {
            if (pSequences[i] > nExpected)
            {
                pRanges[nRangeCount].iStartID = nExpected;
                pRanges[nRangeCount].iEndID = pSequences[i] - 1;
                nRangeCount++;
            }
            nExpected = pSequences[i] + 1;
        }
    }
    else
    {
        // --- 场景 B：回绕序列 ---

        // 【核心】找分界点：找第一个 > 50% INT_MAX 的位置
        // 这里用 50% 作为分界线，比之前的 90% 更宽松，确保能找到分界
        // 原理：回绕数据中，前半段是小数，后半段是大数，分界点就在"从小变大"的转折处
        int iSplitIndex = -1;
        unsigned int midPoint = (unsigned int)INT_MAX / 2; // 10.7亿

        for (int i = 0; i < iCount; i++)
        {
            if ((unsigned int)pSequences[i] > midPoint)
            {
                iSplitIndex = i;
                break;
            }
        }

        if (iSplitIndex > 0)
        {
            // 【分段 1】低区段内部缺失
            int nExpectedLow = pSequences[0] + 1;
            for (int i = 1; i < iSplitIndex; i++)
            {
                if (pSequences[i] > nExpectedLow)
                {
                    pRanges[nRangeCount].iStartID = nExpectedLow;
                    pRanges[nRangeCount].iEndID = pSequences[i] - 1;
                    nRangeCount++;
                }
                nExpectedLow = pSequences[i] + 1;
            }

            // 【分段 2】回绕边界缺失
            int realHighEnd = pSequences[iCount - 1];
            int realLowStart = pSequences[0];

            // 区间 A: realHighEnd + 1 ~ INT_MAX
            if (realHighEnd < INT_MAX)
            {
                pRanges[nRangeCount].iStartID = realHighEnd + 1;
                pRanges[nRangeCount].iEndID = INT_MAX;
                nRangeCount++;
            }

            // 区间 B: 1 ~ realLowStart - 1
            if (realLowStart > 1)
            {
                pRanges[nRangeCount].iStartID = 1;
                pRanges[nRangeCount].iEndID = realLowStart - 1;
                nRangeCount++;
            }

            // 【分段 3】高区段内部缺失
            int nExpectedHigh = pSequences[iSplitIndex] + 1;
            for (int i = iSplitIndex + 1; i < iCount; i++)
            {
                if (pSequences[i] > nExpectedHigh)
                {
                    pRanges[nRangeCount].iStartID = nExpectedHigh;
                    pRanges[nRangeCount].iEndID = pSequences[i] - 1;
                    nRangeCount++;
                }
                nExpectedHigh = pSequences[i] + 1;
            }
        }

        // 【关键】回绕场景排序：高区段在前，低区段在后
        if (nRangeCount > 0)
        {
            MissingRange* pHigh = (MissingRange*)malloc(sizeof(MissingRange) * nRangeCount);
            MissingRange* pLow = (MissingRange*)malloc(sizeof(MissingRange) * nRangeCount);
            int nHigh = 0, nLow = 0;

            for (int i = 0; i < nRangeCount; i++)
            {
                // 用 10 亿作为分界线
                if (pRanges[i].iStartID >= 1000000000)
                    pHigh[nHigh++] = pRanges[i];
                else
                    pLow[nLow++] = pRanges[i];
            }

            // 各自内部升序
            if (nHigh > 1) qsort(pHigh, nHigh, sizeof(MissingRange), CompareRanges);
            if (nLow > 1)  qsort(pLow, nLow, sizeof(MissingRange), CompareRanges);

            // 合并：先高后低
            int k = 0;
            for (int i = 0; i < nHigh; i++) pRanges[k++] = pHigh[i];
            for (int i = 0; i < nLow; i++)  pRanges[k++] = pLow[i];

            free(pHigh);
            free(pLow);
        }
    }

    // 4. 格式化输出
    char szBuffer[8192] = { 0 };
    int nPos = 0;

    for (int i = 0; i < nRangeCount; i++)
    {
        if (nPos > 0) nPos += sprintf_s(szBuffer + nPos, sizeof(szBuffer) - nPos, ",\r\n");

        if (pRanges[i].iStartID == pRanges[i].iEndID)
        {
            nPos += sprintf_s(szBuffer + nPos, sizeof(szBuffer) - nPos, "%d", pRanges[i].iStartID);
        }
        else
        {
            nPos += sprintf_s(szBuffer + nPos, sizeof(szBuffer) - nPos, "%d~%d", pRanges[i].iStartID, pRanges[i].iEndID);
        }
    }

    free(pRanges); // 释放内存

    return (nPos == 0) ? _strdup(STATUS_MISSING_DATA) : _strdup(szBuffer);
}


int CDlgEventReconciliation::FilterSequencesByRange(const CString& strSequences, int iMin, int iMax, CString& strResult)
{
    strResult.Empty(); // 清空输出参数
    if (strSequences.IsEmpty() || strSequences == STATUS_NO_DATA)
    {
        strResult = STATUS_NO_DATA;
        return 0;
    }

    // 特殊标记处理
    if (strSequences == STATUS_MISSING_DATA)
    {
        strResult = STATUS_MISSING_DATA;
        return 0;
    }

    // 1. 解析缺失列表，存入数组以便后续排序和去重处理
    // 预估最大数量：字符串长度 / 2 (保守估计)
    int nMaxCount = strSequences.GetLength() / 2 + 10;
    MissingRange* pResults = new MissingRange[nMaxCount];
    int nResultCount = 0;

    int nPos = 0;
    CString strTemp = strSequences;
    CString strToken;

    // 2. 核心逻辑：计算交集
    bool bDevWrapped = (iMin > iMax); // 判断设备范围是否回绕

    // 3. 遍历所有缺失段
    while (!strTemp.IsEmpty())
    {
        // 支持逗号和换行符分割
        strToken = strTemp.Tokenize(",\r\n", nPos);
        if (strToken.IsEmpty()) break;

        // 去除首尾空格
        strToken.Trim();
        if (strToken.IsEmpty()) continue;

        int iStart = 0, iEnd = 0;
        bool bIsValidRange = false;

        // 解析当前缺失段
        if (strToken.Find('~') != -1)
        {
            // 范围格式：start~end
            if (sscanf_s(strToken, "%d~%d", &iStart, &iEnd) == 2)
            {
                bIsValidRange = true;
            }
        }
        else
        {
            // 单个序号
            iStart = iEnd = atoi(strToken);
            bIsValidRange = true;
        }

        if (!bIsValidRange) continue;

        if (!bDevWrapped)
        {
            // --- 情况 A: 设备范围正常 (Min <= Max) ---
            // 有效范围：[iMin, iMax]
            int iInterStart = (iStart > iMin) ? iStart : iMin;
            int iInterEnd = (iEnd < iMax) ? iEnd : iMax;

            if (iInterStart <= iInterEnd)
            {
                if (nResultCount < nMaxCount)
                {
                    pResults[nResultCount].iStartID = iInterStart;
                    pResults[nResultCount].iEndID = iInterEnd;
                    nResultCount++;
                }
            }
        }
        else
        {
            // --- 情况 B: 设备范围回绕 (Min > Max) ---
            // 有效范围分为两段：
            // 段 1 (高区): [iMin, INT_MAX]
            // 段 2 (低区): [0, iMax]

            // 3.1 尝试与高区段 [iMin, INT_MAX] 求交
            int iInterStartHigh = (iStart > iMin) ? iStart : iMin;
            int iInterEndHigh = (iEnd < INT_MAX) ? iEnd : INT_MAX;

            if (iInterStartHigh <= iInterEndHigh)
            {
                if (nResultCount < nMaxCount)
                {
                    pResults[nResultCount].iStartID = iInterStartHigh;
                    pResults[nResultCount].iEndID = iInterEndHigh;
                    nResultCount++;
                }
            }

            // 3.2 尝试与低区段 [1, iMax] 求交
            int iInterStartLow = (iStart > 1) ? iStart : 1;
            int iInterEndLow = (iEnd < iMax) ? iEnd : iMax;

            if (iInterStartLow <= iInterEndLow)
            {
                if (nResultCount < nMaxCount)
                {
                    pResults[nResultCount].iStartID = iInterStartLow;
                    pResults[nResultCount].iEndID = iInterEndLow;
                    nResultCount++;
                }
            }
        }
    }

    // 如果没有找到任何交集
    if (nResultCount == 0)
    {
        delete[] pResults;
        strResult = STATUS_MISSING_DATA;
        return 0;
    }

    // 4. 【关键步骤】分组与排序
    // 目标：如果是回绕，先显示大数段 (内部升序)，再显示小数段 (内部升序)
    if (bDevWrapped)
    {
        // 分离高区段和低区段
        MissingRange* pHigh = new MissingRange[nResultCount];
        MissingRange* pLow = new MissingRange[nResultCount];
        int nHighCount = 0;
        int nLowCount = 0;

        for (int i = 0; i < nResultCount; i++)
        {
            if (pResults[i].iStartID >= iMin) // 属于高区段
            {
                pHigh[nHighCount++] = pResults[i];
            }
            else // 属于低区段
            {
                pLow[nLowCount++] = pResults[i];
            }
        }

        // 高区段内部升序
        if (nHighCount > 0) qsort(pHigh, nHighCount, sizeof(MissingRange), CompareRanges);
        // 低区段内部升序
        if (nLowCount > 0) qsort(pLow, nLowCount, sizeof(MissingRange), CompareRanges);

        // 合并回 pResults: 先高后低
        int k = 0;
        for (int i = 0; i < nHighCount; i++) pResults[k++] = pHigh[i];
        for (int i = 0; i < nLowCount; i++) pResults[k++] = pLow[i];

        nResultCount = k; // 更新总数

        delete[] pHigh;
        delete[] pLow;
    }
    else
    {
        // 非回绕：全局升序
        if (nResultCount > 0) qsort(pResults, nResultCount, sizeof(MissingRange), CompareRanges);
    }

    // 5. 格式化输出

    for (int i = 0; i < nResultCount; i++)
    {
        if (!strResult.IsEmpty())
        {
            strResult += ",\r\n"; // 保持你原有的换行格式
        }

        if (pResults[i].iStartID == pResults[i].iEndID)
        {
            strResult.AppendFormat("%d", pResults[i].iStartID);
        }
        else
        {
            strResult.AppendFormat("%d~%d", pResults[i].iStartID, pResults[i].iEndID);
        }
    }

    // 6. 清理内存
    delete[] pResults;
    // 返回缺失数量
    return nResultCount;

}

// 将有序的整数数组压缩为 "1~3, 5, 8~10" 格式
// 输入：pSequences (已排序的缺失 ID 列表), iCount (数量)
// 输出：格式化后的字符串指针 (调用者需 free)
char* CDlgEventReconciliation::FormatSequenceRanges(int* pSequences, int iCount)
{
    if (iCount == 0)
        return _strdup(""); // 或者返回 STATUS_NO_DATA 根据你的定义

    // 1. 确保输入是排序的 (虽然调用前通常已排序，但为了安全)
    // 如果调用前保证已排序，这行可以省略以优化性能
    qsort(pSequences, iCount, sizeof(int), CompareInt);

    // 估算缓冲区大小：每个数字最多 10 位 + "~" + "," + "\r\n"
    // 最坏情况每个数字都独立，预留足够空间
    int iBufferSize = iCount * 15 + 100;
    char* szBuffer = (char*)malloc(iBufferSize);
    if (!szBuffer) return NULL;

    memset(szBuffer, 0, iBufferSize);
    int nPos = 0;

    int iStart = pSequences[0];
    int iEnd = pSequences[0];

    for (int i = 1; i < iCount; i++)
    {
        // 如果当前数字是前一个数字 + 1，则延续当前范围
        if (pSequences[i] == iEnd + 1)
        {
            iEnd = pSequences[i];
        }
        else
        {
            // 否则，输出上一个范围，并开始新范围

            // 添加分隔符 (如果不是第一个范围)
            if (nPos > 0)
            {
                nPos += sprintf_s(szBuffer + nPos, iBufferSize - nPos, ",\r\n");
            }

            // 格式化当前范围
            if (iStart == iEnd)
            {
                nPos += sprintf_s(szBuffer + nPos, iBufferSize - nPos, "%d", iStart);
            }
            else
            {
                nPos += sprintf_s(szBuffer + nPos, iBufferSize - nPos, "%d~%d", iStart, iEnd);
            }

            // 重置起点和终点
            iStart = pSequences[i];
            iEnd = pSequences[i];
        }
    }

    // 处理最后一个范围
    if (nPos > 0)
    {
        nPos += sprintf_s(szBuffer + nPos, iBufferSize - nPos, ",\r\n");
    }

    if (iStart == iEnd)
    {
        nPos += sprintf_s(szBuffer + nPos, iBufferSize - nPos, "%d", iStart);
    }
    else
    {
        nPos += sprintf_s(szBuffer + nPos, iBufferSize - nPos, "%d~%d", iStart, iEnd);
    }

    return szBuffer;
}


void CDlgEventReconciliation::FilterExistingSequences()
{
    UpdateData(TRUE);
    // 检查输入是否为空
    if (m_szEventSeq.IsEmpty())
    {
        m_szEventSeqMissing = _T("");
        return;
    }

    // 设置时间范围：当前时间-1天 到 当前时间+1天
    CTime ctNow = CTime::GetCurrentTime();
    CTime ctStart = ctNow - CTimeSpan(1, 0, 0, 0);  // 减1天
    CTime ctEnd = ctNow + CTimeSpan(1, 0, 0, 0);    // 加1天

    time_t tStartTime = ctStart.GetTime();
    time_t tEndTime = ctEnd.GetTime();

    // 1. 使用现有的ParseEventSeq解析输入范围
    CStringA strInputA(m_szEventSeq);
    int* pIDList = NULL;
    int iListSize = 0;
    int iRangeCount = 0;
    MissingRange* pRanges = NULL;

    ParseEventSeq(strInputA.GetString(), &pIDList, &iListSize, &pRanges, &iRangeCount);

    // 2. 收集所有需要检查的序列号
    CArray<int> allSequences;

    // 添加单个数字
    for (int i = 0; i < iListSize; i++)
    {
        allSequences.Add(pIDList[i]);
    }

    // 添加范围内的所有数字
    for (int i = 0; i < iRangeCount; i++)
    {
        for (int seq = pRanges[i].iStartID; seq <= pRanges[i].iEndID; seq++)
        {
            allSequences.Add(seq);
        }
    }

    if (allSequences.GetCount() == 0)
    {
        m_szEventSeqMissing = _T("");
        if (pIDList) free(pIDList);
        if (pRanges) free(pRanges);
        return;
    }

    // 3. 使用现有的文件加载功能获取所有已存在的序列号
    int* pExistingSequences = NULL;
    int iExistingCount = 0;
    int iExistingSize = 0;

    char szDirPath[MAX_PATH];
    char szSearchPattern[MAX_PATH];
    WIN32_FIND_DATA findFileData;
    HANDLE hFind;

    sprintf_s(szDirPath, MAX_PATH, "%s\\%s", g_struLocalParam.chPictureSavePath, "retransmissonInfo");
    sprintf_s(szSearchPattern, MAX_PATH, "%s\\%s_*.json", szDirPath, m_szRetransmissionID);

    hFind = FindFirstFile(szSearchPattern, &findFileData);
    if (hFind != INVALID_HANDLE_VALUE)
    {
        do {
            if (!(findFileData.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY))
            {
                char szFileName[MAX_PATH];
                sprintf_s(szFileName, MAX_PATH, "%s\\%s", szDirPath, findFileData.cFileName);

                if (IsFileDateInRange(szFileName, tStartTime, tEndTime))
                {
                    LoadSequencesFromFile(szFileName, tStartTime, tEndTime,
                        &pExistingSequences, &iExistingCount, &iExistingSize);
                }
            }
        } while (FindNextFile(hFind, &findFileData));
        FindClose(hFind);
    }

    // 4. 过滤：从输入序列号中移除已存在的序列号
    CArray<int> remainingSequences;

    // 如果有已存在的序列号，先排序以便二分查找
    if (iExistingCount > 0)
    {
        qsort(pExistingSequences, iExistingCount, sizeof(int), CompareInt);

        for (int i = 0; i < allSequences.GetCount(); i++)
        {
            int currentSeq = allSequences[i];
            int* pFound = (int*)bsearch(&currentSeq, pExistingSequences, iExistingCount, sizeof(int), CompareInt);

            if (pFound == NULL) // 不存在于已找到的序列号中
            {
                remainingSequences.Add(currentSeq);
            }
        }
    }
    else
    {
        // 如果没有已存在的序列号，所有输入序列号都保留
        for (int i = 0; i < allSequences.GetCount(); i++)
        {
            remainingSequences.Add(allSequences[i]);
        }
    }

    // 5. 使用现有的FormatMissingSequences函数格式化结果
    if (remainingSequences.GetCount() > 0)
    {
        int* pRemainingArray = new int[remainingSequences.GetCount()];
        for (int i = 0; i < remainingSequences.GetCount(); i++)
        {
            pRemainingArray[i] = remainingSequences[i];
        }

        char* szFormatted = FormatSequenceRanges(pRemainingArray, remainingSequences.GetCount());
        m_szEventSeqMissing = CString(szFormatted);
        free(szFormatted);
        delete[] pRemainingArray;
    }
    else
    {
        m_szEventSeqMissing = _T(STATUS_MISSING_DATA); //刷新的过程中，如果全部完成就是补录完成
    }

    // 6. 更新完成比例显示
    int iRemainingCount = remainingSequences.GetCount();
    m_szEventSeqReceivedRate.Format(_T("%d/%d"), m_iMissingNum - iRemainingCount, m_iMissingNum);


    // 8. 清理资源
    if (pIDList) free(pIDList);
    if (pRanges) free(pRanges);
    if (pExistingSequences) free(pExistingSequences);
    UpdateData(FALSE);
}




void CDlgEventReconciliation::OnBnClickedCheckAutoRefresh()
{
    CButton* pCheck = (CButton*)GetDlgItem(IDC_CHECK_AUTO_REFRESH);
    if (pCheck != NULL)
    {
        BOOL bChecked = pCheck->GetCheck();
        int m_nTimerID = 0;
        if (bChecked)
        {
            // 开启定时器，每5秒执行一次（5000毫秒）
            int m_nTimerID = SetTimer(FIND_MISSING_SEQ_TIMER, 5000, NULL);
            if (m_nTimerID != 0)
            {
                TRACE("自动刷新已开启，定时器ID: %d\n", m_nTimerID);
                GetDlgItem(IDC_EDIT_EVENT_SEQUENCE_MISSING)->EnableWindow(FALSE);
                GetDlgItem(IDC_EDIT_EVENT_SEQUENCE)->EnableWindow(FALSE);
                m_bAutoRefresh = true;
                // 立即执行一次查询
                // FilterExistingSequences();
            }
            else
            {
                AfxMessageBox(_T("无法启动定时器！"));
                pCheck->SetCheck(FALSE);
                m_bAutoRefresh = false;
            }
        }
        else
        {
            KillTimer(FIND_MISSING_SEQ_TIMER);
            TRACE("自动刷新已关闭\n");
            GetDlgItem(IDC_EDIT_EVENT_SEQUENCE_MISSING)->EnableWindow(TRUE);
            GetDlgItem(IDC_EDIT_EVENT_SEQUENCE)->EnableWindow(TRUE);
            m_bAutoRefresh = false;
        }
        UpdateData(FALSE);
    }
}

//CString CDlgEventReconciliation::FilterSequencesByRange(const CString& strSequences, int iMin, int iMax)
//{
//    if (strSequences.IsEmpty() || iMin > iMax)
//        return strSequences;
//
//    CString strResult;
//    CString strTemp = strSequences;
//    int nPos = 0;
//    CString strToken;
//
//    // 按行分割
//    while (!strTemp.IsEmpty())
//    {
//        strToken = strTemp.Tokenize(",\r\n", nPos);
//        if (strToken.IsEmpty()) break;
//
//        // 处理单个序号或范围
//        if (strToken.Find('~') != -1)
//        {
//            // 范围格式：start~end
//            int iStart, iEnd;
//            sscanf_s(strToken, "%d~%d", &iStart, &iEnd);
//
//            // 计算与设备范围的交集
//            int iFilteredStart = max(iStart, iMin);
//            int iFilteredEnd = min(iEnd, iMax);
//
//            if (iFilteredStart <= iFilteredEnd)
//            {
//                if (!strResult.IsEmpty()) strResult += ",\r\n";
//                if (iFilteredStart == iFilteredEnd)
//                    strResult.AppendFormat("%d", iFilteredStart);
//                else
//                    strResult.AppendFormat("%d~%d", iFilteredStart, iFilteredEnd);
//            }
//        }
//        else
//        {
//            // 单个序号
//            int iSeq = atoi(strToken);
//            if (iSeq >= iMin && iSeq <= iMax)
//            {
//                if (!strResult.IsEmpty()) strResult += ",\r\n";
//                strResult.AppendFormat("%d", iSeq);
//            }
//        }
//    }
//
//    return strResult.IsEmpty() ? "序列连续" : strResult;
//}

//更新通道list
void CDlgEventReconciliation::UpdateChanStatus()
{
    int iIndex = 0;
    int i = 0;
    CString csTemp;
    m_listChan.DeleteAllItems();
    //get the whole state of all channels

    if (m_iDeviceIndex < 0)
    {
        return;
    }

    for (i = 0; i < g_struDeviceInfo[m_iDeviceIndex].iDeviceChanNum; i++)
    {
        if (i < g_struDeviceInfo[m_iDeviceIndex].iAnalogChanNum)
        {
            csTemp.Format(ANALOG_C_FORMAT, g_struDeviceInfo[m_iDeviceIndex].iStartChan + i);
            m_listChan.InsertItem(iIndex, csTemp);
            m_listChan.SetItemData(iIndex, i + g_struDeviceInfo[m_iDeviceIndex].iStartChan);
            iIndex++;
        }
        else
        {
            csTemp.Format(DIGITAL_C_FORMAT, i + 1 - g_struDeviceInfo[m_iDeviceIndex].iAnalogChanNum/*g_struDeviceInfo[m_iDeviceIndex].iStartChan-g_struDeviceInfo[m_iDeviceIndex].pStruIPParaCfgV40[0].dwStartDChan*/);
            m_listChan.InsertItem(iIndex, csTemp);
            m_listChan.SetItemData(iIndex, i - g_struDeviceInfo[m_iDeviceIndex].iAnalogChanNum + g_struDeviceInfo[m_iDeviceIndex].pStruIPParaCfgV40[0].dwStartDChan);
            iIndex++;
        }
    }
}



void CDlgEventReconciliation::OnBnClickedCheckChanEnabled()
{
    // TODO:  在此添加控件通知处理程序代码
    UpdateData(TRUE);
    GetDlgItem(IDC_LIST_CHANLIST)->EnableWindow(m_bChanEnabled);
}


void CDlgEventReconciliation::GetHistoryEventTypes()
{
    // 获取历史事件类型列表
    NET_DVR_XML_CONFIG_INPUT  xmlConfigInput = { 0 };
    NET_DVR_XML_CONFIG_OUTPUT  xmlCongfigOutput = { 0 };
    xmlConfigInput.dwSize = sizeof(xmlConfigInput);
    xmlCongfigOutput.dwSize = sizeof(xmlCongfigOutput);

    char szUrl[256] = "GET /ISAPI/Event/notification/HistoryEventUploadTask/capabilities?format=json";
    xmlConfigInput.lpRequestUrl = szUrl;
    xmlConfigInput.dwRequestUrlLen = strlen(szUrl);

    DWORD dwOutputLen = 1024 * 1024;
    char *pOutBuf = new char[dwOutputLen];
    memset(pOutBuf, 0, dwOutputLen);

    xmlCongfigOutput.dwOutBufferSize = dwOutputLen;
    xmlCongfigOutput.lpOutBuffer = pOutBuf;

    if (NET_DVR_STDXMLConfig(g_struDeviceInfo[m_iDeviceIndex].lLoginID, &xmlConfigInput, &xmlCongfigOutput))
    {
        // 解析JSON响应
        cJSON* pRoot = cJSON_Parse(pOutBuf);
        if (pRoot != NULL)
        {
            cJSON* pCreateCap = cJSON_GetObjectItem(pRoot, "CreateHistoryEventUploadTaskCap");
            if (pCreateCap != NULL)
            {
                cJSON* pEventList = cJSON_GetObjectItem(pCreateCap, "eventList");
                if (pEventList != NULL)
                {
                    cJSON* pEventType = cJSON_GetObjectItem(pEventList, "eventType");
                    if (pEventType != NULL)
                    {
                        cJSON* pOptArray = cJSON_GetObjectItem(pEventType, "@opt");
                        if (pOptArray != NULL)
                        {
                            m_listEventType.DeleteAllItems();
                            int nCount = cJSON_GetArraySize(pOptArray);
                            for (int i = 0; i < nCount; i++)
                            {
                                cJSON* pItem = cJSON_GetArrayItem(pOptArray, i);
                                if (pItem != NULL)
                                {
                                    int nIndex = m_listEventType.InsertItem(i, pItem->valuestring);
                                    m_listEventType.SetItemData(nIndex, i);
                                }
                            }
                        }
                    }
                }
            }
            cJSON_Delete(pRoot);
        }
    }
    else
    {
     
        DWORD dwError = NET_DVR_GetLastError();
        //CString strError;
        //strError.Format("Create history event upload task failed, error code: %d", dwError);
        g_pMainDlg->AddLog(m_iDeviceIndex, OPERATION_FAIL_T, "NET_DVR_STDXMLConfig");

    }

    delete[] pOutBuf;
    pOutBuf = NULL;
}

void CDlgEventReconciliation::OnBnClickedBtnHiseventUpload()
{
    // TODO:  在此添加控件通知处理程序代码
    UpdateData(TRUE);

    if (m_bHisEventUploading)
    {
        // 取消历史补录
        CancelHistoryEventUpload();
    }
    else
    {
        // 开始历史补录
        StartHistoryEventUpload();
    }
}


bool CDlgEventReconciliation::StartHistoryEventUpload()
{
    // 构建JSON请求报文
    cJSON* pRoot = cJSON_CreateObject();

    // taskID - 可选，如果为空则由设备生成
    m_szHisEventTaskID = "test12345";
    if (!m_szHisEventTaskID.IsEmpty())
    {
        cJSON_AddStringToObject(pRoot, "taskID", m_szHisEventTaskID);
    }

    // retransmissionID - 必需
    cJSON_AddStringToObject(pRoot, "retransmissionID", m_szHisEventRetransmissionID);

    // eventMode - 必需
    cJSON_AddStringToObject(pRoot, "eventMode", m_szHisEventUploadMode);

    // eventList - 当eventMode为"list"时必需
    if (m_szHisEventUploadMode == "list")
    {
        cJSON* pEventList = cJSON_CreateArray();
        for (int i = 0; i < m_listEventType.GetItemCount(); i++)
        {
            if (m_listEventType.GetCheck(i))
            {
                cJSON* pEvent = cJSON_CreateObject();
                CString strEventType = m_listEventType.GetItemText(i, 0);
                cJSON_AddStringToObject(pEvent, "eventType", strEventType);
                cJSON_AddItemToArray(pEventList, pEvent);
            }
        }
        cJSON_AddItemToObject(pRoot, "eventList", pEventList);
    }

    // channels - 可选，当选择部分通道时
    if (m_bChanEnabled)
    {
        CString strParam, strChannel = _T("");
        BOOL bFirst = TRUE;
        for (int i = 0; i < m_listChan.GetItemCount(); i++)
        {
            if (m_listChan.GetCheck(i))
            {
                int iChannel = -1;
                iChannel = NET_DVR_SDKChannelToISAPI(g_struDeviceInfo[m_iDeviceIndex].lLoginID, m_listChan.GetItemData(i), TRUE);
                if (bFirst)
                {
                    strChannel.Format("%d", iChannel);
                    bFirst = FALSE;
                }
                else
                {
                    strChannel.Format(",%d", iChannel);
                }
                strParam += strChannel;
            }
        }

        if (!strParam.IsEmpty())
        {
            cJSON* pChannels = cJSON_CreateArray();
            CStringArray arrChannels;
            SplitString(strParam, ",", arrChannels);
            for (int i = 0; i < arrChannels.GetSize(); i++)
            {
                cJSON_AddItemToArray(pChannels, cJSON_CreateNumber(_ttoi(arrChannels[i])));
            }
            cJSON_AddItemToObject(pRoot, "channels", pChannels);
        }
    }

    // timeSpanList - 必需
    cJSON* pTimeSpanList = cJSON_CreateArray();
    cJSON* pTimeSpan = cJSON_CreateObject();

    // 格式化时间
    CString strStartTime = FormatISOTime(m_ctHisEventDateStart, m_ctHisEventTimeStart);
    CString strEndTime = FormatISOTime(m_ctHisEventDateStop, m_ctHisEventTimeStop);

    cJSON_AddStringToObject(pTimeSpan, "startTime", strStartTime);
    cJSON_AddStringToObject(pTimeSpan, "endTime", strEndTime);
    cJSON_AddItemToArray(pTimeSpanList, pTimeSpan);
    cJSON_AddItemToObject(pRoot, "timeSpanList", pTimeSpanList);

    // 发送请求
    char* szJsonRequest = cJSON_Print(pRoot);
    DWORD dwInputLen = strlen(szJsonRequest);

    NET_DVR_XML_CONFIG_INPUT xmlInput = { 0 };
    NET_DVR_XML_CONFIG_OUTPUT xmlOutput = { 0 };
    xmlInput.dwSize = sizeof(NET_DVR_XML_CONFIG_INPUT);
    xmlOutput.dwSize = sizeof(NET_DVR_XML_CONFIG_OUTPUT);

    char* strUrl = "POST /ISAPI/Event/notification/CreateHistoryEventUploadTask?format=json\r\n";
    xmlInput.lpRequestUrl = strUrl;
    xmlInput.dwRequestUrlLen = strlen(strUrl);

    xmlInput.lpInBuffer = szJsonRequest;
    xmlInput.dwInBufferSize = dwInputLen;

    DWORD dwOutputLen = 1024 * 1024;
    char* pOutBuf = new char[dwOutputLen];
    memset(pOutBuf, 0, dwOutputLen);
    xmlOutput.lpOutBuffer = pOutBuf;
    xmlOutput.dwOutBufferSize = dwOutputLen;

    BOOL bResult = NET_DVR_STDXMLConfig(g_struDeviceInfo[m_iDeviceIndex].lLoginID, &xmlInput, &xmlOutput);

    bool bRet = false;
    if (bResult)
    {
        CString strError;
        strError.Format(_T("NET_DVR_STDXMLConfig(%s)"), strUrl);
        g_pMainDlg->AddLog(m_iDeviceIndex, OPERATION_SUCC_T, strError);

        cJSON* pRootResp = cJSON_Parse(pOutBuf);
        cJSON* pStatus = cJSON_GetObjectItem(pRootResp, "statusString");
        if (pRootResp != NULL)
        {
            cJSON* pTaskID = cJSON_GetObjectItem(pRootResp, "taskID");
            if (pTaskID != NULL)
            {
                m_szHisEventTaskID = pTaskID->valuestring;
                // 更新界面
                m_bHisEventUploading = TRUE;
                char szButtonNameTemp[8] = { 0 };
                g_StringLanType(szButtonNameTemp, "取消", "Cancel");
                GetDlgItem(IDC_BTN_HISEVENT_UPLOAD)->SetWindowText(_T(szButtonNameTemp));
                SetTimer(HIS_EVENT_UPLOAD_TIMER, 1000, NULL); // 启动进度查询定时器
            } 
           
            else if (pStatus != NULL && strcmp(pStatus->valuestring, "OK") != 0)
            {
                CString strError;
                strError.Format("Create history event upload task failed: %s", pStatus ? pStatus->valuestring : "Unknown error");
                g_pMainDlg->AddLog(m_iDeviceIndex, OPERATION_FAIL_T, strError);
            }
            cJSON_Delete(pRootResp);
        }
    }
    else
    {
        CString strError;
        strError.Format(_T("NET_DVR_STDXMLConfig(%s)"), strUrl);
        g_pMainDlg->AddLog(m_iDeviceIndex, OPERATION_FAIL_T, strError);
    }

    // 清理资源
    cJSON_Delete(pRoot);
    free(szJsonRequest);
    delete[] pOutBuf;

    return bRet;
}

CString CDlgEventReconciliation::FormatISOTime(const CTime& date, const CTime& time)
{
    CString strTime;
    strTime.Format(_T("%04d-%02d-%02dT%02d:%02d:%02d.000+08:00"),
        date.GetYear(), date.GetMonth(), date.GetDay(),
        time.GetHour(), time.GetMinute(), time.GetSecond());
    return strTime;
}

void CDlgEventReconciliation::SplitString(const CString& str, const CString& delimiter, CStringArray& result)
{
    int nPos = 0;
    CString strToken = str.Tokenize(delimiter, nPos);
    while (!strToken.IsEmpty())
    {
        result.Add(strToken);
        strToken = str.Tokenize(delimiter, nPos);
    }
}
void CDlgEventReconciliation::GetHistoryEventUploadProgress()
{
    if (m_szHisEventTaskID.IsEmpty())
        return;
     
    // 构建查询请求
    cJSON* pRoot = cJSON_CreateObject();
    cJSON_AddStringToObject(pRoot, "taskID", m_szHisEventTaskID);

    char* szJsonRequest = cJSON_Print(pRoot);

    NET_DVR_XML_CONFIG_INPUT xmlInput = { 0 };
    NET_DVR_XML_CONFIG_OUTPUT xmlOutput = { 0 };
    xmlInput.dwSize = sizeof(NET_DVR_XML_CONFIG_INPUT);
    xmlOutput.dwSize = sizeof(NET_DVR_XML_CONFIG_OUTPUT);

    char* strUrl = "POST /ISAPI/Event/notification/GetHistoryEventUploadTaskStatus?format=json\r\n";
    xmlInput.lpRequestUrl = strUrl;
    xmlInput.dwRequestUrlLen = strlen(strUrl);


    xmlInput.lpInBuffer = szJsonRequest;
    xmlInput.dwInBufferSize = strlen(szJsonRequest);

    DWORD dwOutputLen = 1024 * 1024;
    char* pOutBuf = new char[dwOutputLen];
    memset(pOutBuf, 0, dwOutputLen);
    xmlOutput.lpOutBuffer = pOutBuf;
    xmlOutput.dwOutBufferSize = dwOutputLen;

    if (NET_DVR_STDXMLConfig(g_struDeviceInfo[m_iDeviceIndex].lLoginID, &xmlInput, &xmlOutput))
    {
        CString strError;
        strError.Format(_T("NET_DVR_STDXMLConfig(%s)"), strUrl);
        g_pMainDlg->AddLog(m_iDeviceIndex, OPERATION_SUCC_T, strError);
        cJSON* pRootResp = cJSON_Parse(pOutBuf);
        if (pRootResp != NULL)
        {
            CString strProgressInfo;
            CString strTemp;
            cJSON* pProgress = cJSON_GetObjectItem(pRootResp, "progress");
            if (pProgress != NULL)
            {
                int nProgress = pProgress->valueint;
                strTemp.Format(_T("%d%%"), nProgress);
                strProgressInfo += strTemp;
                UpdateData(FALSE);

                // 进度完成时停止定时器并重置界面
                if (nProgress >= 100)
                {
                    KillTimer(HIS_EVENT_UPLOAD_TIMER);
                    m_bHisEventUploading = FALSE;
                    char szButtonNameTemp[8] = { 0 };
                    g_StringLanType(szButtonNameTemp, "开始", "Start");
                    GetDlgItem(IDC_BTN_HISEVENT_UPLOAD)->SetWindowText(_T(szButtonNameTemp));
                    m_szHisEventTaskID.Empty();
                }
            }
            // 解析total和remainingNum（在同一行显示）
            cJSON* pTotal = cJSON_GetObjectItem(pRootResp, "total");
            cJSON* pRemainingNum = cJSON_GetObjectItem(pRootResp, "remainingNum");
            if (pTotal != NULL && pRemainingNum != NULL )
            {
                strTemp.Format(_T("(total:%d, remian:%d)"),
                    pTotal->valueint, pRemainingNum->valueint);
                strProgressInfo += strTemp;
            }

            //// 解析eventSequenceRange（在新行显示）
            //cJSON* pEventSequenceRange = cJSON_GetObjectItem(pRootResp, "eventSequenceRange");
            //if (pEventSequenceRange != NULL)
            //{
            //    cJSON* pStartSequenceID = cJSON_GetObjectItem(pEventSequenceRange, "startSequenceID");
            //    cJSON* pEndSequenceID = cJSON_GetObjectItem(pEventSequenceRange, "endSequenceID");

            //    if (pStartSequenceID != NULL  && pEndSequenceID != NULL )
            //    {
            //        strTemp.Format(_T(" | Seq Range: %d - %d"),
            //            pStartSequenceID->valueint, pEndSequenceID->valueint);
            //        strProgressInfo += strTemp;
            //    }
            //}

            // 更新显示
            if (!strProgressInfo.IsEmpty())
            {
                m_szHisEventUploadProgress = strProgressInfo;
                UpdateData(FALSE);
            }
            cJSON_Delete(pRootResp);
        }
    }
    else
    {
        CString strError;
        strError.Format(_T("NET_DVR_STDXMLConfig(%s)"), strUrl);
        g_pMainDlg->AddLog(m_iDeviceIndex, OPERATION_FAIL_T, strError);
    }

    free(szJsonRequest);
    delete[] pOutBuf;
}

bool CDlgEventReconciliation::CancelHistoryEventUpload()
{
    if (m_szHisEventTaskID.IsEmpty())
        return false;

    // 构建取消请求
    cJSON* pRoot = cJSON_CreateObject();
    cJSON_AddStringToObject(pRoot, "taskID", m_szHisEventTaskID);

    char* szJsonRequest = cJSON_Print(pRoot);

    NET_DVR_XML_CONFIG_INPUT xmlInput = { 0 };
    NET_DVR_XML_CONFIG_OUTPUT xmlOutput = { 0 };
    xmlInput.dwSize = sizeof(NET_DVR_XML_CONFIG_INPUT);
    xmlOutput.dwSize = sizeof(NET_DVR_XML_CONFIG_OUTPUT);

    char* strUrl = "PUT /ISAPI/Event/notification/CancelHistoryEventUploadTask?format=json\r\n";
    xmlInput.lpRequestUrl = strUrl;
    xmlInput.dwRequestUrlLen = strlen(strUrl);

    xmlInput.lpInBuffer = szJsonRequest;
    xmlInput.dwInBufferSize = strlen(szJsonRequest);

    DWORD dwOutputLen = 1024;
    char* pOutBuf = new char[dwOutputLen];
    memset(pOutBuf, 0, dwOutputLen);
    xmlOutput.lpOutBuffer = pOutBuf;
    xmlOutput.dwOutBufferSize = dwOutputLen;

    BOOL bResult = NET_DVR_STDXMLConfig(g_struDeviceInfo[m_iDeviceIndex].lLoginID, &xmlInput, &xmlOutput);

    bool bRet = false;
    if (bResult)
    {
        CString strError;
        strError.Format(_T("NET_DVR_STDXMLConfig(%s)"), strUrl);
        g_pMainDlg->AddLog(m_iDeviceIndex, OPERATION_SUCC_T, strError);
        cJSON* pRootResp = cJSON_Parse(pOutBuf);
        if (pRootResp != NULL)
        {
            cJSON* pStatus = cJSON_GetObjectItem(pRootResp, "statusString");
            if (pStatus != NULL && strcmp(pStatus->valuestring, "OK") == 0)
            {
                bRet = true;
                // 停止定时器并重置界面
                KillTimer(HIS_EVENT_UPLOAD_TIMER);
                m_bHisEventUploading = FALSE;
                char szButtonNameTemp[8] = { 0 };
                g_StringLanType(szButtonNameTemp, "开始", "Start");
                GetDlgItem(IDC_BTN_HISEVENT_UPLOAD)->SetWindowText(_T(szButtonNameTemp));
                m_szHisEventTaskID.Empty();
                m_szHisEventUploadProgress = _T("Cancelled");
                UpdateData(FALSE);
            }
            cJSON_Delete(pRootResp);
        }
    }
    else
    {
        CString strError;
        strError.Format(_T("NET_DVR_STDXMLConfig(%s)"), strUrl);
        g_pMainDlg->AddLog(m_iDeviceIndex, OPERATION_FAIL_T, strError);
    }

    free(szJsonRequest);
    delete[] pOutBuf;
    return bRet;
}

