/**********************************************************
FileName:    DlgRemoteRecordSchedule.cpp
Description: remote record schedule      
Date:        2008/05/17
Note: 		<Global>struct, macro refer to GeneralDef.h, global variants and API refer to ClientDemo.cpp      
Modification History:      
    <version> <time>         <desc>
    <1.0    > <2008/05/17>       <created>
***********************************************************/


#include "stdafx.h"
#include "ClientDemo.h"
#include "DlgRemoteRecordSchedule.h"
#include ".\dlgremoterecordschedule.h"


// CDlgRemoteRecordSchedule dialog

/*********************************************************
  Function:	CDlgRemoteRecordSchedule
  Desc:		Constructor
  Input:	
  Output:	
  Return:	
**********************************************************/
IMPLEMENT_DYNAMIC(CDlgRemoteRecordSchedule, CDialog)
CDlgRemoteRecordSchedule::CDlgRemoteRecordSchedule(CWnd* pParent /*=NULL*/)
	: CDialog(CDlgRemoteRecordSchedule::IDD, pParent)
	, m_bCheckAllDay(FALSE)
	, m_iHour11(0)
	, m_iMin11(0)
	, m_iHour12(0)
	, m_iMin12(0)
	, m_iHour21(0)
	, m_iMin21(0)
	, m_iHour22(0)
	, m_iMin22(0)
	, m_iHour31(0)
	, m_iMin31(0)
	, m_iHour32(0)
	, m_iMin32(0)
	, m_iHour41(0)
	, m_iMin41(0)
	, m_iHour42(0)
	, m_iMin42(0)
	, m_iHour51(0)
	, m_iMin51(0)
	, m_iHour52(0)
	, m_iMin52(0)
	, m_iHour61(0)
	, m_iMin61(0)
	, m_iHour62(0)
	, m_iMin62(0)
	, m_iHour71(0)
	, m_iMin71(0)
	, m_iHour72(0)
	, m_iMin72(0)
	, m_iHour81(0)
	, m_iMin81(0)
	, m_iHour82(0)
	, m_iMin82(0)
	, m_nDate(0)
	, m_nCopyDate(0)
	, m_struRemoteRecSchedule(NULL)
{
    m_lServerID = -1;
    m_lChannel = -1; 
    m_iDevIndex = -1;
    memset(&m_struHolidayRecord, 0, sizeof(m_struHolidayRecord));
}

/*********************************************************
  Function:	~CDlgRemoteRecordSchedule
  Desc:		destructor
  Input:	
  Output:	
  Return:	
**********************************************************/
CDlgRemoteRecordSchedule::~CDlgRemoteRecordSchedule()
{
}

/*********************************************************
Function:	TimeTest
Desc:		check time settings
Input:	
Output:	
Return:	TRUE,correct schedule;FALSE,incorrect schedule;
**********************************************************/
BOOL CDlgRemoteRecordSchedule::TimeTest()
{
	int i = 0;
	int j = 0;
	WORD wStartTime[MAX_TIMESEGMENT_V30], wStopTime[MAX_TIMESEGMENT_V30];
	char szLan[128] = {0};
	UpdateData(TRUE);
	if ((m_iHour11 < 0) || (m_iHour11 > 24) || (m_iHour12 < 0) || (m_iHour12 > 24) ||	\
		(m_iHour21 < 0) || (m_iHour21 > 24) || (m_iHour22 < 0) || (m_iHour22 > 24) ||	\
		(m_iHour31 < 0) || (m_iHour31 > 24) || (m_iHour32 < 0) || (m_iHour32 > 24) ||	\
		(m_iHour41 < 0) || (m_iHour41 > 24) || (m_iHour42 < 0) || (m_iHour42 > 24) ||   \
		(m_iHour51 < 0) || (m_iHour51 > 24) || (m_iHour52 < 0) || (m_iHour52 > 24) ||	\
		(m_iHour61 < 0) || (m_iHour61 > 24) || (m_iHour62 < 0) || (m_iHour62 > 24) ||	\
		(m_iHour71 < 0) || (m_iHour71 > 24) || (m_iHour72 < 0) || (m_iHour72 > 24) ||	\
		(m_iHour81 < 0) || (m_iHour81 > 24) || (m_iHour82 < 0) || (m_iHour82 > 24))
	{
		g_StringLanType(szLan, "小时范围在0 -- 24之间", "Hour between 0 - 24 ");
		AfxMessageBox(szLan);
		return FALSE;
	}
	if ((m_iMin11 < 0) || (m_iMin11 > 60) || (m_iMin12 < 0) || (m_iMin12 > 60) ||	\
		(m_iMin21 < 0) || (m_iMin21 > 60) || (m_iMin22 < 0) || (m_iMin22 > 60) ||	\
		(m_iMin31 < 0) || (m_iMin31 > 60) || (m_iMin32 < 0) || (m_iMin32 > 60) ||	\
		(m_iMin41 < 0) || (m_iMin41 > 60) || (m_iMin42 < 0) || (m_iMin42 > 60) ||   \
		(m_iMin51 < 0) || (m_iMin51 > 60) || (m_iMin52 < 0) || (m_iMin52 > 60) ||	\
		(m_iMin61 < 0) || (m_iMin61 > 60) || (m_iMin62 < 0) || (m_iMin62 > 60) ||	\
		(m_iMin71 < 0) || (m_iMin71 > 60) || (m_iMin72 < 0) || (m_iMin72 > 60) ||	\
		(m_iMin81 < 0) || (m_iMin81 > 60) || (m_iMin82 < 0) || (m_iMin82 > 60))
	{
		g_StringLanType(szLan, "分钟范围在0 -- 60之间", "Minute between 0 - 60 ");
		AfxMessageBox(szLan);
		return FALSE;
	}
	wStartTime[0] = (WORD)(m_iHour11 * 100 + m_iMin11);
	wStartTime[1] = (WORD)(m_iHour21 * 100 + m_iMin21);
	wStartTime[2] = (WORD)(m_iHour31 * 100 + m_iMin31);
	wStartTime[3] = (WORD)(m_iHour41 * 100 + m_iMin41);
	wStopTime[0] = (WORD)(m_iHour12 * 100 + m_iMin12);
	wStopTime[1] = (WORD)(m_iHour22 * 100 + m_iMin22);
	wStopTime[2] = (WORD)(m_iHour32 * 100 + m_iMin32);
	wStopTime[3] = (WORD)(m_iHour42 * 100 + m_iMin42);
	wStartTime[4] = (WORD)(m_iHour51 * 100 + m_iMin51);
	wStartTime[5] = (WORD)(m_iHour61 * 100 + m_iMin61);
	wStartTime[6] = (WORD)(m_iHour71 * 100 + m_iMin71);
	wStartTime[7] = (WORD)(m_iHour81 * 100 + m_iMin81);
	wStopTime[4] = (WORD)(m_iHour52 * 100 + m_iMin52);
	wStopTime[5] = (WORD)(m_iHour62 * 100 + m_iMin62);
	wStopTime[6] = (WORD)(m_iHour72 * 100 + m_iMin72);
	wStopTime[7] = (WORD)(m_iHour82 * 100 + m_iMin82);
	for (i = 0; i < MAX_TIMESEGMENT_V30; i++)
	{
		if ((wStartTime[i] > 2400) || (wStopTime[i] > 2400))
		{
			g_StringLanType(szLan, "布防时间不能超过24:00", "Fortify time can not be more than 24:00");
			AfxMessageBox(szLan);
			return FALSE;
		}
		if (wStartTime[i] > wStopTime[i])
		{
			g_StringLanType(szLan, "布防起始时间不能大于停止时间", "Fortify start time can not be larger than the record to stop time");
			AfxMessageBox(szLan);
			return FALSE;
		}
		for (j = 0; j < MAX_TIMESEGMENT_V30; j++)
		{
			if (i == j)
			{
				continue;
			}
			if ((wStartTime[i] > wStartTime[j]) && (wStartTime[i] < wStopTime[j]) ||	\
				(wStopTime[i] > wStartTime[j]) && (wStopTime[i] < wStopTime[j]))
			{
				g_StringLanType(szLan, "时间段不能重复", "time can not be repeated");
				AfxMessageBox(szLan);
				return FALSE;
			}
		}
	}
	return TRUE;
}

/*********************************************************
Function:	DoDataExchange
Desc:		the map between control and variable
Input:	
Output:	
Return:	
**********************************************************/
void CDlgRemoteRecordSchedule::DoDataExchange(CDataExchange* pDX)
{
	CDialog::DoDataExchange(pDX);
	//{{AFX_DATA_MAP(CDlgRemoteRecordSchedule)
	DDX_Control(pDX, IDC_COMBO_WEEK_DAY, m_comboWeekday);
	DDX_Check(pDX, IDC_CHK_ALL_DAY, m_bCheckAllDay);
	DDX_Control(pDX, IDC_COMBO_ALL_DAY_TYPE, m_comboAllDayType);
	DDX_Text(pDX, IDC_EDIT_HOUR11, m_iHour11);
	DDX_Text(pDX, IDC_EDIT_MIN11, m_iMin11);
	DDX_Text(pDX, IDC_EDIT_HOUR12, m_iHour12);
	DDX_Text(pDX, IDC_EDIT_MIN12, m_iMin12);
	DDX_Text(pDX, IDC_EDIT_HOUR21, m_iHour21);
	DDX_Text(pDX, IDC_EDIT_MIN21, m_iMin21);
	DDX_Text(pDX, IDC_EDIT_HOUR22, m_iHour22);
	DDX_Text(pDX, IDC_EDIT_MIN22, m_iMin22);
	DDX_Text(pDX, IDC_EDIT_HOUR31, m_iHour31);
	DDX_Text(pDX, IDC_EDIT_MIN31, m_iMin31);
	DDX_Text(pDX, IDC_EDIT_HOUR32, m_iHour32);
	DDX_Text(pDX, IDC_EDIT_MIN32, m_iMin32);
	DDX_Text(pDX, IDC_EDIT_HOUR41, m_iHour41);
	DDX_Text(pDX, IDC_EDIT_MIN41, m_iMin41);
	DDX_Text(pDX, IDC_EDIT_HOUR42, m_iHour42);
	DDX_Text(pDX, IDC_EDIT_MIN42, m_iMin42);
	DDX_Text(pDX, IDC_EDIT_HOUR51, m_iHour51);
	DDX_Text(pDX, IDC_EDIT_MIN51, m_iMin51);
	DDX_Text(pDX, IDC_EDIT_HOUR52, m_iHour52);
	DDX_Text(pDX, IDC_EDIT_MIN52, m_iMin52);
	DDX_Text(pDX, IDC_EDIT_HOUR61, m_iHour61);
	DDX_Text(pDX, IDC_EDIT_MIN61, m_iMin61);
	DDX_Text(pDX, IDC_EDIT_HOUR62, m_iHour62);
	DDX_Text(pDX, IDC_EDIT_MIN62, m_iMin62);
	DDX_Text(pDX, IDC_EDIT_HOUR71, m_iHour71);
	DDX_Text(pDX, IDC_EDIT_MIN71, m_iMin71);
	DDX_Text(pDX, IDC_EDIT_HOUR72, m_iHour72);
	DDX_Text(pDX, IDC_EDIT_MIN72, m_iMin72);
	DDX_Text(pDX, IDC_EDIT_HOUR81, m_iHour81);
	DDX_Text(pDX, IDC_EDIT_MIN81, m_iMin81);
	DDX_Text(pDX, IDC_EDIT_HOUR82, m_iHour82);
	DDX_Text(pDX, IDC_EDIT_MIN82, m_iMin82);
	DDX_Control(pDX, IDC_COMBO_TIME_REC_TYPE1, m_comboTimeRecType1);
	DDX_Control(pDX, IDC_COMBO_TIME_REC_TYPE2, m_comboTimeRecType2);
	DDX_Control(pDX, IDC_COMBO_TIME_REC_TYPE3, m_comboTimeRecType3);
	DDX_Control(pDX, IDC_COMBO_TIME_REC_TYPE4, m_comboTimeRecType4);
	DDX_Control(pDX, IDC_COMBO_COPY_WEEKDAY, m_comboCopyWeekday);
	DDX_Control(pDX, IDC_COMBO_TIME_REC_TYPE5, m_comboTimeRecType5);
	DDX_Control(pDX, IDC_COMBO_TIME_REC_TYPE6, m_comboTimeRecType6);
	DDX_Control(pDX, IDC_COMBO_TIME_REC_TYPE7, m_comboTimeRecType7);
	DDX_Control(pDX, IDC_COMBO_TIME_REC_TYPE8, m_comboTimeRecType8);
    //}}AFX_DATA_MAP
}


/*********************************************************
Function:	BEGIN_MESSAGE_MAP
Desc:		the map between control and function
Input:	
Output:	
Return:	
**********************************************************/
BEGIN_MESSAGE_MAP(CDlgRemoteRecordSchedule, CDialog)
	//{{AFX_MSG_MAP(CDlgRemoteRecordSchedule)	
	ON_BN_CLICKED(ID_BTN_REMOTE_REC_OK, OnBnClickedBtnRemoteRecOk)
	ON_BN_CLICKED(ID_BTN_REMOTE_REC_EXIT, OnBnClickedBtnRemoteRecExit)
	ON_BN_CLICKED(IDC_BTN_REMOTE_REC_COPY, OnBnClickedBtnRemoteRecCopy)
	ON_CBN_SELCHANGE(IDC_COMBO_WEEK_DAY, OnCbnSelchangeComboWeekDay)
	ON_BN_CLICKED(IDC_CHK_ALL_DAY, OnBnClickedChkAllDay)
	//}}AFX_MSG_MAP	
END_MESSAGE_MAP()


// CDlgRemoteRecordSchedule message handlers
/*********************************************************
Function:	OnInitDialog
Desc:		Initialize the dialog
Input:	
Output:	
Return:	
**********************************************************/
BOOL CDlgRemoteRecordSchedule::OnInitDialog() 
{
	CDialog::OnInitDialog();

	// TODO: Add extra initialization here
	int nIndex = 0;
	char szLan[128] = {0};
	int i;
	m_comboAllDayType.ResetContent();
	m_comboTimeRecType1.ResetContent();
	m_comboTimeRecType2.ResetContent();
	m_comboTimeRecType3.ResetContent();
	m_comboTimeRecType4.ResetContent();
	m_comboTimeRecType5.ResetContent();
	m_comboTimeRecType6.ResetContent();
	m_comboTimeRecType7.ResetContent();
	m_comboTimeRecType8.ResetContent();

	g_StringLanType(szLan, "定时录像","Timing");
    m_comboAllDayType.InsertString(nIndex, szLan);
    m_comboAllDayType.SetItemData(nIndex, 0);
	m_comboTimeRecType1.InsertString(nIndex, szLan);
    m_comboTimeRecType1.SetItemData(nIndex, 0);
	m_comboTimeRecType2.InsertString(nIndex, szLan);
    m_comboTimeRecType2.SetItemData(nIndex, 0);
	m_comboTimeRecType3.InsertString(nIndex, szLan);
    m_comboTimeRecType3.SetItemData(nIndex, 0);
	m_comboTimeRecType4.InsertString(nIndex, szLan);
    m_comboTimeRecType4.SetItemData(nIndex, 0);
	m_comboTimeRecType5.InsertString(nIndex, szLan);
    m_comboTimeRecType5.SetItemData(nIndex, 0);
	m_comboTimeRecType6.InsertString(nIndex, szLan);
    m_comboTimeRecType6.SetItemData(nIndex, 0);
	m_comboTimeRecType7.InsertString(nIndex, szLan);
    m_comboTimeRecType7.SetItemData(nIndex, 0);
	m_comboTimeRecType8.InsertString(nIndex, szLan);
    m_comboTimeRecType8.SetItemData(nIndex, 0);
    nIndex++;

	g_StringLanType(szLan, "移动侦测录像","Motion");
    m_comboAllDayType.InsertString(nIndex, szLan);
    m_comboAllDayType.SetItemData(nIndex, 1);
	m_comboTimeRecType1.InsertString(nIndex, szLan);
    m_comboTimeRecType1.SetItemData(nIndex,1);
	m_comboTimeRecType2.InsertString(nIndex, szLan);
    m_comboTimeRecType2.SetItemData(nIndex, 1);
	m_comboTimeRecType3.InsertString(nIndex, szLan);
    m_comboTimeRecType3.SetItemData(nIndex, 1);
	m_comboTimeRecType4.InsertString(nIndex, szLan);
    m_comboTimeRecType4.SetItemData(nIndex, 1);
	m_comboTimeRecType5.InsertString(nIndex, szLan);
    m_comboTimeRecType5.SetItemData(nIndex, 1);
	m_comboTimeRecType6.InsertString(nIndex, szLan);
    m_comboTimeRecType6.SetItemData(nIndex, 1);
	m_comboTimeRecType7.InsertString(nIndex, szLan);
    m_comboTimeRecType7.SetItemData(nIndex, 1);
	m_comboTimeRecType8.InsertString(nIndex, szLan);
    m_comboTimeRecType8.SetItemData(nIndex, 1);
    nIndex++;

	g_StringLanType(szLan, "报警录像","Alarm");
    m_comboAllDayType.InsertString(nIndex, szLan);
    m_comboAllDayType.SetItemData(nIndex, 2);
	m_comboTimeRecType1.InsertString(nIndex, szLan);
    m_comboTimeRecType1.SetItemData(nIndex,2);
	m_comboTimeRecType2.InsertString(nIndex, szLan);
    m_comboTimeRecType2.SetItemData(nIndex, 2);
	m_comboTimeRecType3.InsertString(nIndex, szLan);
    m_comboTimeRecType3.SetItemData(nIndex, 2);
	m_comboTimeRecType4.InsertString(nIndex, szLan);
    m_comboTimeRecType4.SetItemData(nIndex, 2);
	m_comboTimeRecType5.InsertString(nIndex, szLan);
    m_comboTimeRecType5.SetItemData(nIndex, 2);
	m_comboTimeRecType6.InsertString(nIndex, szLan);
    m_comboTimeRecType6.SetItemData(nIndex, 2);
	m_comboTimeRecType7.InsertString(nIndex, szLan);
    m_comboTimeRecType7.SetItemData(nIndex, 2);
	m_comboTimeRecType8.InsertString(nIndex, szLan);
    m_comboTimeRecType8.SetItemData(nIndex, 2);
    nIndex++;

	g_StringLanType(szLan, "移动侦测|报警录像","Motion or Alarm");
    m_comboAllDayType.InsertString(nIndex, szLan);
    m_comboAllDayType.SetItemData(nIndex, 3);
	m_comboTimeRecType1.InsertString(nIndex, szLan);
    m_comboTimeRecType1.SetItemData(nIndex,3);
	m_comboTimeRecType2.InsertString(nIndex, szLan);
    m_comboTimeRecType2.SetItemData(nIndex, 3);
	m_comboTimeRecType3.InsertString(nIndex, szLan);
    m_comboTimeRecType3.SetItemData(nIndex, 3);
	m_comboTimeRecType4.InsertString(nIndex, szLan);
    m_comboTimeRecType4.SetItemData(nIndex, 3);
	m_comboTimeRecType5.InsertString(nIndex, szLan);
    m_comboTimeRecType5.SetItemData(nIndex, 3);
	m_comboTimeRecType6.InsertString(nIndex, szLan);
    m_comboTimeRecType6.SetItemData(nIndex, 3);
	m_comboTimeRecType7.InsertString(nIndex, szLan);
    m_comboTimeRecType7.SetItemData(nIndex, 3);
	m_comboTimeRecType8.InsertString(nIndex, szLan);
    m_comboTimeRecType8.SetItemData(nIndex, 3);
    nIndex++;

	g_StringLanType(szLan, "移动侦测&报警录像","Motion and alarm");
    m_comboAllDayType.InsertString(nIndex, szLan);
    m_comboAllDayType.SetItemData(nIndex, 4);
	m_comboTimeRecType1.InsertString(nIndex, szLan);
    m_comboTimeRecType1.SetItemData(nIndex,4);
	m_comboTimeRecType2.InsertString(nIndex, szLan);
    m_comboTimeRecType2.SetItemData(nIndex, 4);
	m_comboTimeRecType3.InsertString(nIndex, szLan);
    m_comboTimeRecType3.SetItemData(nIndex, 4);
	m_comboTimeRecType4.InsertString(nIndex, szLan);
    m_comboTimeRecType4.SetItemData(nIndex, 4);
	m_comboTimeRecType5.InsertString(nIndex, szLan);
    m_comboTimeRecType5.SetItemData(nIndex, 4);
	m_comboTimeRecType6.InsertString(nIndex, szLan);
    m_comboTimeRecType6.SetItemData(nIndex, 4);
	m_comboTimeRecType7.InsertString(nIndex, szLan);
    m_comboTimeRecType7.SetItemData(nIndex, 4);
	m_comboTimeRecType8.InsertString(nIndex, szLan);
    m_comboTimeRecType8.SetItemData(nIndex, 4);
    nIndex++;

	g_StringLanType(szLan, "命令触发录像","Command");
    m_comboAllDayType.InsertString(nIndex, szLan);
    m_comboAllDayType.SetItemData(nIndex, 5);
	m_comboTimeRecType1.InsertString(nIndex, szLan);
    m_comboTimeRecType1.SetItemData(nIndex,5);
	m_comboTimeRecType2.InsertString(nIndex, szLan);
    m_comboTimeRecType2.SetItemData(nIndex, 5);
	m_comboTimeRecType3.InsertString(nIndex, szLan);
    m_comboTimeRecType3.SetItemData(nIndex, 5);
	m_comboTimeRecType4.InsertString(nIndex, szLan);
    m_comboTimeRecType4.SetItemData(nIndex, 5);
	m_comboTimeRecType5.InsertString(nIndex, szLan);
    m_comboTimeRecType5.SetItemData(nIndex, 5);
	m_comboTimeRecType6.InsertString(nIndex, szLan);
    m_comboTimeRecType6.SetItemData(nIndex, 5);
	m_comboTimeRecType7.InsertString(nIndex, szLan);
    m_comboTimeRecType7.SetItemData(nIndex, 5);
	m_comboTimeRecType8.InsertString(nIndex, szLan);
    m_comboTimeRecType8.SetItemData(nIndex, 5);
    nIndex++;

	g_StringLanType(szLan, "智能录像","VCA");
    m_comboAllDayType.InsertString(nIndex, szLan);
    m_comboAllDayType.SetItemData(nIndex, 6);
	m_comboTimeRecType1.InsertString(nIndex, szLan);
    m_comboTimeRecType1.SetItemData(nIndex,6);
	m_comboTimeRecType2.InsertString(nIndex, szLan);
    m_comboTimeRecType2.SetItemData(nIndex, 6);
	m_comboTimeRecType3.InsertString(nIndex, szLan);
    m_comboTimeRecType3.SetItemData(nIndex, 6);
	m_comboTimeRecType4.InsertString(nIndex, szLan);
    m_comboTimeRecType4.SetItemData(nIndex, 6);
	m_comboTimeRecType5.InsertString(nIndex, szLan);
    m_comboTimeRecType5.SetItemData(nIndex, 6);
	m_comboTimeRecType6.InsertString(nIndex, szLan);
    m_comboTimeRecType6.SetItemData(nIndex, 6);
	m_comboTimeRecType7.InsertString(nIndex, szLan);
    m_comboTimeRecType7.SetItemData(nIndex, 6);
	m_comboTimeRecType8.InsertString(nIndex, szLan);
    m_comboTimeRecType8.SetItemData(nIndex, 6);
    nIndex++;

	g_StringLanType(szLan, "PIR报警录像","PIR alarm");
    m_comboAllDayType.InsertString(nIndex, szLan);
    m_comboAllDayType.SetItemData(nIndex, 10);
	m_comboTimeRecType1.InsertString(nIndex, szLan);
    m_comboTimeRecType1.SetItemData(nIndex,10);
	m_comboTimeRecType2.InsertString(nIndex, szLan);
    m_comboTimeRecType2.SetItemData(nIndex, 10);
	m_comboTimeRecType3.InsertString(nIndex, szLan);
    m_comboTimeRecType3.SetItemData(nIndex, 10);
	m_comboTimeRecType4.InsertString(nIndex, szLan);
    m_comboTimeRecType4.SetItemData(nIndex, 10);
	m_comboTimeRecType5.InsertString(nIndex, szLan);
    m_comboTimeRecType5.SetItemData(nIndex, 10);
	m_comboTimeRecType6.InsertString(nIndex, szLan);
    m_comboTimeRecType6.SetItemData(nIndex, 10);
	m_comboTimeRecType7.InsertString(nIndex, szLan);
    m_comboTimeRecType7.SetItemData(nIndex, 10);
	m_comboTimeRecType8.InsertString(nIndex, szLan);
    m_comboTimeRecType8.SetItemData(nIndex, 10);
    nIndex++;

	g_StringLanType(szLan, "无线报警录像","Wireless alarm");
    m_comboAllDayType.InsertString(nIndex, szLan);
    m_comboAllDayType.SetItemData(nIndex, 11);
	m_comboTimeRecType1.InsertString(nIndex, szLan);
    m_comboTimeRecType1.SetItemData(nIndex,11);
	m_comboTimeRecType2.InsertString(nIndex, szLan);
    m_comboTimeRecType2.SetItemData(nIndex, 11);
	m_comboTimeRecType3.InsertString(nIndex, szLan);
    m_comboTimeRecType3.SetItemData(nIndex, 11);
	m_comboTimeRecType4.InsertString(nIndex, szLan);
    m_comboTimeRecType4.SetItemData(nIndex, 11);
	m_comboTimeRecType5.InsertString(nIndex, szLan);
    m_comboTimeRecType5.SetItemData(nIndex, 11);
	m_comboTimeRecType6.InsertString(nIndex, szLan);
    m_comboTimeRecType6.SetItemData(nIndex, 11);
	m_comboTimeRecType7.InsertString(nIndex, szLan);
    m_comboTimeRecType7.SetItemData(nIndex, 11);
	m_comboTimeRecType8.InsertString(nIndex, szLan);
    m_comboTimeRecType8.SetItemData(nIndex, 11);
    nIndex++;

	g_StringLanType(szLan, "呼救报警录像","Call help alarm");
    m_comboAllDayType.InsertString(nIndex, szLan);
    m_comboAllDayType.SetItemData(nIndex, 12);
	m_comboTimeRecType1.InsertString(nIndex, szLan);
    m_comboTimeRecType1.SetItemData(nIndex,12);
	m_comboTimeRecType2.InsertString(nIndex, szLan);
    m_comboTimeRecType2.SetItemData(nIndex, 12);
	m_comboTimeRecType3.InsertString(nIndex, szLan);
    m_comboTimeRecType3.SetItemData(nIndex, 12);
	m_comboTimeRecType4.InsertString(nIndex, szLan);
    m_comboTimeRecType4.SetItemData(nIndex, 12);
	m_comboTimeRecType5.InsertString(nIndex, szLan);
    m_comboTimeRecType5.SetItemData(nIndex, 12);
	m_comboTimeRecType6.InsertString(nIndex, szLan);
    m_comboTimeRecType6.SetItemData(nIndex, 12);
	m_comboTimeRecType7.InsertString(nIndex, szLan);
    m_comboTimeRecType7.SetItemData(nIndex, 12);
	m_comboTimeRecType8.InsertString(nIndex, szLan);
    m_comboTimeRecType8.SetItemData(nIndex, 12);
    nIndex++;

	g_StringLanType(szLan, "全部事件报警录像","Command");
    m_comboAllDayType.InsertString(nIndex, szLan);
    m_comboAllDayType.SetItemData(nIndex, 13);
	m_comboTimeRecType1.InsertString(nIndex, szLan);
    m_comboTimeRecType1.SetItemData(nIndex,13);
	m_comboTimeRecType2.InsertString(nIndex, szLan);
    m_comboTimeRecType2.SetItemData(nIndex, 13);
	m_comboTimeRecType3.InsertString(nIndex, szLan);
    m_comboTimeRecType3.SetItemData(nIndex, 13);
	m_comboTimeRecType4.InsertString(nIndex, szLan);
    m_comboTimeRecType4.SetItemData(nIndex, 13);
	m_comboTimeRecType5.InsertString(nIndex, szLan);
    m_comboTimeRecType5.SetItemData(nIndex, 13);
	m_comboTimeRecType6.InsertString(nIndex, szLan);
    m_comboTimeRecType6.SetItemData(nIndex, 13);
	m_comboTimeRecType7.InsertString(nIndex, szLan);
    m_comboTimeRecType7.SetItemData(nIndex, 13);
	m_comboTimeRecType8.InsertString(nIndex, szLan);
    m_comboTimeRecType8.SetItemData(nIndex, 13);
    nIndex++;

	g_StringLanType(szLan, "智能交通事件报警","Command");
    m_comboAllDayType.InsertString(nIndex, szLan);
    m_comboAllDayType.SetItemData(nIndex, 14);
	m_comboTimeRecType1.InsertString(nIndex, szLan);
    m_comboTimeRecType1.SetItemData(nIndex,14);
	m_comboTimeRecType2.InsertString(nIndex, szLan);
    m_comboTimeRecType2.SetItemData(nIndex, 14);
	m_comboTimeRecType3.InsertString(nIndex, szLan);
    m_comboTimeRecType3.SetItemData(nIndex, 14);
	m_comboTimeRecType4.InsertString(nIndex, szLan);
    m_comboTimeRecType4.SetItemData(nIndex, 14);
	m_comboTimeRecType5.InsertString(nIndex, szLan);
    m_comboTimeRecType5.SetItemData(nIndex, 14);
	m_comboTimeRecType6.InsertString(nIndex, szLan);
    m_comboTimeRecType6.SetItemData(nIndex, 14);
	m_comboTimeRecType7.InsertString(nIndex, szLan);
    m_comboTimeRecType7.SetItemData(nIndex, 14);
	m_comboTimeRecType8.InsertString(nIndex, szLan);
    m_comboTimeRecType8.SetItemData(nIndex, 14);
    nIndex++;

//#ifdef NET_DVR_GET_TRAVERSE_PLANE_DETECTION
	g_StringLanType(szLan, "越界侦测","NULL");
    m_comboAllDayType.InsertString(nIndex, szLan);
    m_comboAllDayType.SetItemData(nIndex, 15);
	m_comboTimeRecType1.InsertString(nIndex, szLan);
    m_comboTimeRecType1.SetItemData(nIndex,15);
	m_comboTimeRecType2.InsertString(nIndex, szLan);
    m_comboTimeRecType2.SetItemData(nIndex, 15);
	m_comboTimeRecType3.InsertString(nIndex, szLan);
    m_comboTimeRecType3.SetItemData(nIndex, 15);
	m_comboTimeRecType4.InsertString(nIndex, szLan);
    m_comboTimeRecType4.SetItemData(nIndex, 15);
	m_comboTimeRecType5.InsertString(nIndex, szLan);
    m_comboTimeRecType5.SetItemData(nIndex, 15);
	m_comboTimeRecType6.InsertString(nIndex, szLan);
    m_comboTimeRecType6.SetItemData(nIndex, 15);
	m_comboTimeRecType7.InsertString(nIndex, szLan);
    m_comboTimeRecType7.SetItemData(nIndex, 15);
	m_comboTimeRecType8.InsertString(nIndex, szLan);
    m_comboTimeRecType8.SetItemData(nIndex, 15);
    nIndex++;
//#endif //NET_DVR_GET_TRAVERSE_PLANE_DETECTION
	
	g_StringLanType(szLan, "区域入侵","Field Detection");
    m_comboAllDayType.InsertString(nIndex, szLan);
    m_comboAllDayType.SetItemData(nIndex, 16);
	m_comboTimeRecType1.InsertString(nIndex, szLan);
    m_comboTimeRecType1.SetItemData(nIndex,16);
	m_comboTimeRecType2.InsertString(nIndex, szLan);
    m_comboTimeRecType2.SetItemData(nIndex, 16);
	m_comboTimeRecType3.InsertString(nIndex, szLan);
    m_comboTimeRecType3.SetItemData(nIndex, 16);
	m_comboTimeRecType4.InsertString(nIndex, szLan);
    m_comboTimeRecType4.SetItemData(nIndex, 16);
	m_comboTimeRecType5.InsertString(nIndex, szLan);
    m_comboTimeRecType5.SetItemData(nIndex, 16);
	m_comboTimeRecType6.InsertString(nIndex, szLan);
    m_comboTimeRecType6.SetItemData(nIndex, 16);
	m_comboTimeRecType7.InsertString(nIndex, szLan);
    m_comboTimeRecType7.SetItemData(nIndex, 16);
	m_comboTimeRecType8.InsertString(nIndex, szLan);
    m_comboTimeRecType8.SetItemData(nIndex, 16);
    nIndex++;
	
	g_StringLanType(szLan, "声音异常","Audio Exception");
    m_comboAllDayType.InsertString(nIndex, szLan);
    m_comboAllDayType.SetItemData(nIndex, 17);
	m_comboTimeRecType1.InsertString(nIndex, szLan);
    m_comboTimeRecType1.SetItemData(nIndex,17);
	m_comboTimeRecType2.InsertString(nIndex, szLan);
    m_comboTimeRecType2.SetItemData(nIndex, 17);
	m_comboTimeRecType3.InsertString(nIndex, szLan);
    m_comboTimeRecType3.SetItemData(nIndex, 17);
	m_comboTimeRecType4.InsertString(nIndex, szLan);
    m_comboTimeRecType4.SetItemData(nIndex, 17);
	m_comboTimeRecType5.InsertString(nIndex, szLan);
    m_comboTimeRecType5.SetItemData(nIndex, 17);
	m_comboTimeRecType6.InsertString(nIndex, szLan);
    m_comboTimeRecType6.SetItemData(nIndex, 17);
	m_comboTimeRecType7.InsertString(nIndex, szLan);
    m_comboTimeRecType7.SetItemData(nIndex, 17);
	m_comboTimeRecType8.InsertString(nIndex, szLan);
    m_comboTimeRecType8.SetItemData(nIndex, 17);
    nIndex++;

	g_StringLanType(szLan, "场景变更侦测","Scene Change Detection");//2013-07-17 场景变更侦测录像计划
    m_comboAllDayType.InsertString(nIndex, szLan);
    m_comboAllDayType.SetItemData(nIndex, 18);
	m_comboTimeRecType1.InsertString(nIndex, szLan);
    m_comboTimeRecType1.SetItemData(nIndex,18);
	m_comboTimeRecType2.InsertString(nIndex, szLan);
    m_comboTimeRecType2.SetItemData(nIndex, 18);
	m_comboTimeRecType3.InsertString(nIndex, szLan);
    m_comboTimeRecType3.SetItemData(nIndex, 18);
	m_comboTimeRecType4.InsertString(nIndex, szLan);
    m_comboTimeRecType4.SetItemData(nIndex, 18);
	m_comboTimeRecType5.InsertString(nIndex, szLan);
    m_comboTimeRecType5.SetItemData(nIndex, 18);
	m_comboTimeRecType6.InsertString(nIndex, szLan);
    m_comboTimeRecType6.SetItemData(nIndex, 18);
	m_comboTimeRecType7.InsertString(nIndex, szLan);
    m_comboTimeRecType7.SetItemData(nIndex, 18);
	m_comboTimeRecType8.InsertString(nIndex, szLan);
    m_comboTimeRecType8.SetItemData(nIndex, 18);
    nIndex++;

	g_StringLanType(szLan, "智能侦测","Intelligent detectionn"); 
    m_comboAllDayType.InsertString(nIndex, szLan);
    m_comboAllDayType.SetItemData(nIndex, 19);
	m_comboTimeRecType1.InsertString(nIndex, szLan);
    m_comboTimeRecType1.SetItemData(nIndex,19);
	m_comboTimeRecType2.InsertString(nIndex, szLan);
    m_comboTimeRecType2.SetItemData(nIndex, 19);
	m_comboTimeRecType3.InsertString(nIndex, szLan);
    m_comboTimeRecType3.SetItemData(nIndex, 19);
	m_comboTimeRecType4.InsertString(nIndex, szLan);
    m_comboTimeRecType4.SetItemData(nIndex, 19);
	m_comboTimeRecType5.InsertString(nIndex, szLan);
    m_comboTimeRecType5.SetItemData(nIndex, 19);
	m_comboTimeRecType6.InsertString(nIndex, szLan);
    m_comboTimeRecType6.SetItemData(nIndex, 19);
	m_comboTimeRecType7.InsertString(nIndex, szLan);
    m_comboTimeRecType7.SetItemData(nIndex, 19);
	m_comboTimeRecType8.InsertString(nIndex, szLan);
    m_comboTimeRecType8.SetItemData(nIndex, 19);
    nIndex++;
	
	g_StringLanType(szLan, "人脸侦测","Face Detection"); //20140224 人脸侦测
    m_comboAllDayType.InsertString(nIndex, szLan);
    m_comboAllDayType.SetItemData(nIndex, 20);
	m_comboTimeRecType1.InsertString(nIndex, szLan);
    m_comboTimeRecType1.SetItemData(nIndex,20);
	m_comboTimeRecType2.InsertString(nIndex, szLan);
    m_comboTimeRecType2.SetItemData(nIndex, 20);
	m_comboTimeRecType3.InsertString(nIndex, szLan);
    m_comboTimeRecType3.SetItemData(nIndex, 20);
	m_comboTimeRecType4.InsertString(nIndex, szLan);
    m_comboTimeRecType4.SetItemData(nIndex, 20);
	m_comboTimeRecType5.InsertString(nIndex, szLan);
    m_comboTimeRecType5.SetItemData(nIndex, 20);
	m_comboTimeRecType6.InsertString(nIndex, szLan);
    m_comboTimeRecType6.SetItemData(nIndex, 20);
	m_comboTimeRecType7.InsertString(nIndex, szLan);
    m_comboTimeRecType7.SetItemData(nIndex, 20);
	m_comboTimeRecType8.InsertString(nIndex, szLan);
    m_comboTimeRecType8.SetItemData(nIndex, 20);
    nIndex++;

    g_StringLanType(szLan, "POS录像", "POS Record");
    m_comboAllDayType.InsertString(nIndex, szLan);
    m_comboAllDayType.SetItemData(nIndex, 21);
    m_comboTimeRecType1.InsertString(nIndex, szLan);
    m_comboTimeRecType1.SetItemData(nIndex, 21);
    m_comboTimeRecType2.InsertString(nIndex, szLan);
    m_comboTimeRecType2.SetItemData(nIndex, 21);
    m_comboTimeRecType3.InsertString(nIndex, szLan);
    m_comboTimeRecType3.SetItemData(nIndex, 21);
    m_comboTimeRecType4.InsertString(nIndex, szLan);
    m_comboTimeRecType4.SetItemData(nIndex, 21);
    m_comboTimeRecType5.InsertString(nIndex, szLan);
    m_comboTimeRecType5.SetItemData(nIndex, 21);
    m_comboTimeRecType6.InsertString(nIndex, szLan);
    m_comboTimeRecType6.SetItemData(nIndex, 21);
    m_comboTimeRecType7.InsertString(nIndex, szLan);
    m_comboTimeRecType7.SetItemData(nIndex, 21);
    m_comboTimeRecType8.InsertString(nIndex, szLan);
    m_comboTimeRecType8.SetItemData(nIndex, 21);
    nIndex++;
	
    g_StringLanType(szLan, "进入区域侦测", "Enter region detection");
    m_comboAllDayType.InsertString(nIndex, szLan);
    m_comboAllDayType.SetItemData(nIndex, 22);
    m_comboTimeRecType1.InsertString(nIndex, szLan);
    m_comboTimeRecType1.SetItemData(nIndex, 22);
    m_comboTimeRecType2.InsertString(nIndex, szLan);
    m_comboTimeRecType2.SetItemData(nIndex, 22);
    m_comboTimeRecType3.InsertString(nIndex, szLan);
    m_comboTimeRecType3.SetItemData(nIndex, 22);
    m_comboTimeRecType4.InsertString(nIndex, szLan);
    m_comboTimeRecType4.SetItemData(nIndex, 22);
    m_comboTimeRecType5.InsertString(nIndex, szLan);
    m_comboTimeRecType5.SetItemData(nIndex, 22);
    m_comboTimeRecType6.InsertString(nIndex, szLan);
    m_comboTimeRecType6.SetItemData(nIndex, 22);
    m_comboTimeRecType7.InsertString(nIndex, szLan);
    m_comboTimeRecType7.SetItemData(nIndex, 22);
    m_comboTimeRecType8.InsertString(nIndex, szLan);
    m_comboTimeRecType8.SetItemData(nIndex, 22);
    nIndex++;

    g_StringLanType(szLan, "离开区域侦测", "Leave region detection");
    m_comboAllDayType.InsertString(nIndex, szLan);
    m_comboAllDayType.SetItemData(nIndex, 23);
    m_comboTimeRecType1.InsertString(nIndex, szLan);
    m_comboTimeRecType1.SetItemData(nIndex, 23);
    m_comboTimeRecType2.InsertString(nIndex, szLan);
    m_comboTimeRecType2.SetItemData(nIndex, 23);
    m_comboTimeRecType3.InsertString(nIndex, szLan);
    m_comboTimeRecType3.SetItemData(nIndex, 23);
    m_comboTimeRecType4.InsertString(nIndex, szLan);
    m_comboTimeRecType4.SetItemData(nIndex, 23);
    m_comboTimeRecType5.InsertString(nIndex, szLan);
    m_comboTimeRecType5.SetItemData(nIndex, 23);
    m_comboTimeRecType6.InsertString(nIndex, szLan);
    m_comboTimeRecType6.SetItemData(nIndex, 23);
    m_comboTimeRecType7.InsertString(nIndex, szLan);
    m_comboTimeRecType7.SetItemData(nIndex, 23);
    m_comboTimeRecType8.InsertString(nIndex, szLan);
    m_comboTimeRecType8.SetItemData(nIndex, 23);
    nIndex++;

    g_StringLanType(szLan, "徘徊侦测", "Hovering detection");
    m_comboAllDayType.InsertString(nIndex, szLan);
    m_comboAllDayType.SetItemData(nIndex, 24);
    m_comboTimeRecType1.InsertString(nIndex, szLan);
    m_comboTimeRecType1.SetItemData(nIndex, 24);
    m_comboTimeRecType2.InsertString(nIndex, szLan);
    m_comboTimeRecType2.SetItemData(nIndex, 24);
    m_comboTimeRecType3.InsertString(nIndex, szLan);
    m_comboTimeRecType3.SetItemData(nIndex, 24);
    m_comboTimeRecType4.InsertString(nIndex, szLan);
    m_comboTimeRecType4.SetItemData(nIndex, 24);
    m_comboTimeRecType5.InsertString(nIndex, szLan);
    m_comboTimeRecType5.SetItemData(nIndex, 24);
    m_comboTimeRecType6.InsertString(nIndex, szLan);
    m_comboTimeRecType6.SetItemData(nIndex, 24);
    m_comboTimeRecType7.InsertString(nIndex, szLan);
    m_comboTimeRecType7.SetItemData(nIndex, 24);
    m_comboTimeRecType8.InsertString(nIndex, szLan);
    m_comboTimeRecType8.SetItemData(nIndex, 24);
    nIndex++;

    g_StringLanType(szLan, "人员聚集侦测", "Researchers gathered detection");
    m_comboAllDayType.InsertString(nIndex, szLan);
    m_comboAllDayType.SetItemData(nIndex, 25);
    m_comboTimeRecType1.InsertString(nIndex, szLan);
    m_comboTimeRecType1.SetItemData(nIndex, 25);
    m_comboTimeRecType2.InsertString(nIndex, szLan);
    m_comboTimeRecType2.SetItemData(nIndex, 25);
    m_comboTimeRecType3.InsertString(nIndex, szLan);
    m_comboTimeRecType3.SetItemData(nIndex, 25);
    m_comboTimeRecType4.InsertString(nIndex, szLan);
    m_comboTimeRecType4.SetItemData(nIndex, 25);
    m_comboTimeRecType5.InsertString(nIndex, szLan);
    m_comboTimeRecType5.SetItemData(nIndex, 25);
    m_comboTimeRecType6.InsertString(nIndex, szLan);
    m_comboTimeRecType6.SetItemData(nIndex, 25);
    m_comboTimeRecType7.InsertString(nIndex, szLan);
    m_comboTimeRecType7.SetItemData(nIndex, 25);
    m_comboTimeRecType8.InsertString(nIndex, szLan);
    m_comboTimeRecType8.SetItemData(nIndex, 25);
    nIndex++;

    g_StringLanType(szLan, "快速运动侦测", "Fast motion detection");
    m_comboAllDayType.InsertString(nIndex, szLan);
    m_comboAllDayType.SetItemData(nIndex, 26);
    m_comboTimeRecType1.InsertString(nIndex, szLan);
    m_comboTimeRecType1.SetItemData(nIndex, 26);
    m_comboTimeRecType2.InsertString(nIndex, szLan);
    m_comboTimeRecType2.SetItemData(nIndex, 26);
    m_comboTimeRecType3.InsertString(nIndex, szLan);
    m_comboTimeRecType3.SetItemData(nIndex, 26);
    m_comboTimeRecType4.InsertString(nIndex, szLan);
    m_comboTimeRecType4.SetItemData(nIndex, 26);
    m_comboTimeRecType5.InsertString(nIndex, szLan);
    m_comboTimeRecType5.SetItemData(nIndex, 26);
    m_comboTimeRecType6.InsertString(nIndex, szLan);
    m_comboTimeRecType6.SetItemData(nIndex, 26);
    m_comboTimeRecType7.InsertString(nIndex, szLan);
    m_comboTimeRecType7.SetItemData(nIndex, 26);
    m_comboTimeRecType8.InsertString(nIndex, szLan);
    m_comboTimeRecType8.SetItemData(nIndex, 26);
    nIndex++;

    g_StringLanType(szLan, "停车侦测", "Parking detection");
    m_comboAllDayType.InsertString(nIndex, szLan);
    m_comboAllDayType.SetItemData(nIndex, 27);
    m_comboTimeRecType1.InsertString(nIndex, szLan);
    m_comboTimeRecType1.SetItemData(nIndex, 27);
    m_comboTimeRecType2.InsertString(nIndex, szLan);
    m_comboTimeRecType2.SetItemData(nIndex, 27);
    m_comboTimeRecType3.InsertString(nIndex, szLan);
    m_comboTimeRecType3.SetItemData(nIndex, 27);
    m_comboTimeRecType4.InsertString(nIndex, szLan);
    m_comboTimeRecType4.SetItemData(nIndex, 27);
    m_comboTimeRecType5.InsertString(nIndex, szLan);
    m_comboTimeRecType5.SetItemData(nIndex, 27);
    m_comboTimeRecType6.InsertString(nIndex, szLan);
    m_comboTimeRecType6.SetItemData(nIndex, 27);
    m_comboTimeRecType7.InsertString(nIndex, szLan);
    m_comboTimeRecType7.SetItemData(nIndex, 27);
    m_comboTimeRecType8.InsertString(nIndex, szLan);
    m_comboTimeRecType8.SetItemData(nIndex, 27);
    nIndex++;

    g_StringLanType(szLan, "物品遗留侦测", "Goods Legacy Detection");
    m_comboAllDayType.InsertString(nIndex, szLan);
    m_comboAllDayType.SetItemData(nIndex, 28);
    m_comboTimeRecType1.InsertString(nIndex, szLan);
    m_comboTimeRecType1.SetItemData(nIndex, 28);
    m_comboTimeRecType2.InsertString(nIndex, szLan);
    m_comboTimeRecType2.SetItemData(nIndex, 28);
    m_comboTimeRecType3.InsertString(nIndex, szLan);
    m_comboTimeRecType3.SetItemData(nIndex, 28);
    m_comboTimeRecType4.InsertString(nIndex, szLan);
    m_comboTimeRecType4.SetItemData(nIndex, 28);
    m_comboTimeRecType5.InsertString(nIndex, szLan);
    m_comboTimeRecType5.SetItemData(nIndex, 28);
    m_comboTimeRecType6.InsertString(nIndex, szLan);
    m_comboTimeRecType6.SetItemData(nIndex, 28);
    m_comboTimeRecType7.InsertString(nIndex, szLan);
    m_comboTimeRecType7.SetItemData(nIndex, 28);
    m_comboTimeRecType8.InsertString(nIndex, szLan);
    m_comboTimeRecType8.SetItemData(nIndex, 28);
    nIndex++;

    g_StringLanType(szLan, "物品拿取侦测", "Goods Take Detection");
    m_comboAllDayType.InsertString(nIndex, szLan);
    m_comboAllDayType.SetItemData(nIndex, 29);
    m_comboTimeRecType1.InsertString(nIndex, szLan);
    m_comboTimeRecType1.SetItemData(nIndex, 29);
    m_comboTimeRecType2.InsertString(nIndex, szLan);
    m_comboTimeRecType2.SetItemData(nIndex, 29);
    m_comboTimeRecType3.InsertString(nIndex, szLan);
    m_comboTimeRecType3.SetItemData(nIndex, 29);
    m_comboTimeRecType4.InsertString(nIndex, szLan);
    m_comboTimeRecType4.SetItemData(nIndex, 29);
    m_comboTimeRecType5.InsertString(nIndex, szLan);
    m_comboTimeRecType5.SetItemData(nIndex, 29);
    m_comboTimeRecType6.InsertString(nIndex, szLan);
    m_comboTimeRecType6.SetItemData(nIndex, 29);
    m_comboTimeRecType7.InsertString(nIndex, szLan);
    m_comboTimeRecType7.SetItemData(nIndex, 29);
    m_comboTimeRecType8.InsertString(nIndex, szLan);
    m_comboTimeRecType8.SetItemData(nIndex, 29);
    nIndex++;

    g_StringLanType(szLan, "火点检测", "Fire detection");
    m_comboAllDayType.InsertString(nIndex, szLan);
    m_comboAllDayType.SetItemData(nIndex, 30);
    m_comboTimeRecType1.InsertString(nIndex, szLan);
    m_comboTimeRecType1.SetItemData(nIndex, 30);
    m_comboTimeRecType2.InsertString(nIndex, szLan);
    m_comboTimeRecType2.SetItemData(nIndex, 30);
    m_comboTimeRecType3.InsertString(nIndex, szLan);
    m_comboTimeRecType3.SetItemData(nIndex, 30);
    m_comboTimeRecType4.InsertString(nIndex, szLan);
    m_comboTimeRecType4.SetItemData(nIndex, 30);
    m_comboTimeRecType5.InsertString(nIndex, szLan);
    m_comboTimeRecType5.SetItemData(nIndex, 30);
    m_comboTimeRecType6.InsertString(nIndex, szLan);
    m_comboTimeRecType6.SetItemData(nIndex, 30);
    m_comboTimeRecType7.InsertString(nIndex, szLan);
    m_comboTimeRecType7.SetItemData(nIndex, 30);
    m_comboTimeRecType8.InsertString(nIndex, szLan);
    m_comboTimeRecType8.SetItemData(nIndex, 30);
    nIndex++;

    g_StringLanType(szLan, "防破坏检测", "VandalProof detection");
    m_comboAllDayType.InsertString(nIndex, szLan);
    m_comboAllDayType.SetItemData(nIndex, 31);
    m_comboTimeRecType1.InsertString(nIndex, szLan);
    m_comboTimeRecType1.SetItemData(nIndex, 31);
    m_comboTimeRecType2.InsertString(nIndex, szLan);
    m_comboTimeRecType2.SetItemData(nIndex, 31);
    m_comboTimeRecType3.InsertString(nIndex, szLan);
    m_comboTimeRecType3.SetItemData(nIndex, 31);
    m_comboTimeRecType4.InsertString(nIndex, szLan);
    m_comboTimeRecType4.SetItemData(nIndex, 31);
    m_comboTimeRecType5.InsertString(nIndex, szLan);
    m_comboTimeRecType5.SetItemData(nIndex, 31);
    m_comboTimeRecType6.InsertString(nIndex, szLan);
    m_comboTimeRecType6.SetItemData(nIndex, 31);
    m_comboTimeRecType7.InsertString(nIndex, szLan);
    m_comboTimeRecType7.SetItemData(nIndex, 31);
    m_comboTimeRecType8.InsertString(nIndex, szLan);
    m_comboTimeRecType8.SetItemData(nIndex, 31);
    nIndex++;

    g_StringLanType(szLan, "打架斗殴事件", "Fight events");
    m_comboAllDayType.InsertString(nIndex, szLan);
    m_comboAllDayType.SetItemData(nIndex, 32);
    m_comboTimeRecType1.InsertString(nIndex, szLan);
    m_comboTimeRecType1.SetItemData(nIndex, 32);
    m_comboTimeRecType2.InsertString(nIndex, szLan);
    m_comboTimeRecType2.SetItemData(nIndex, 32);
    m_comboTimeRecType3.InsertString(nIndex, szLan);
    m_comboTimeRecType3.SetItemData(nIndex, 32);
    m_comboTimeRecType4.InsertString(nIndex, szLan);
    m_comboTimeRecType4.SetItemData(nIndex, 32);
    m_comboTimeRecType5.InsertString(nIndex, szLan);
    m_comboTimeRecType5.SetItemData(nIndex, 32);
    m_comboTimeRecType6.InsertString(nIndex, szLan);
    m_comboTimeRecType6.SetItemData(nIndex, 32);
    m_comboTimeRecType7.InsertString(nIndex, szLan);
    m_comboTimeRecType7.SetItemData(nIndex, 32);
    m_comboTimeRecType8.InsertString(nIndex, szLan);
    m_comboTimeRecType8.SetItemData(nIndex, 32);
    nIndex++;

    g_StringLanType(szLan, "起身事件", "Start events");
    m_comboAllDayType.InsertString(nIndex, szLan);
    m_comboAllDayType.SetItemData(nIndex, 33);
    m_comboTimeRecType1.InsertString(nIndex, szLan);
    m_comboTimeRecType1.SetItemData(nIndex, 33);
    m_comboTimeRecType2.InsertString(nIndex, szLan);
    m_comboTimeRecType2.SetItemData(nIndex, 33);
    m_comboTimeRecType3.InsertString(nIndex, szLan);
    m_comboTimeRecType3.SetItemData(nIndex, 33);
    m_comboTimeRecType4.InsertString(nIndex, szLan);
    m_comboTimeRecType4.SetItemData(nIndex, 33);
    m_comboTimeRecType5.InsertString(nIndex, szLan);
    m_comboTimeRecType5.SetItemData(nIndex, 33);
    m_comboTimeRecType6.InsertString(nIndex, szLan);
    m_comboTimeRecType6.SetItemData(nIndex, 33);
    m_comboTimeRecType7.InsertString(nIndex, szLan);
    m_comboTimeRecType7.SetItemData(nIndex, 33);
    m_comboTimeRecType8.InsertString(nIndex, szLan);
    m_comboTimeRecType8.SetItemData(nIndex, 33);
    nIndex++;

    g_StringLanType(szLan, "瞌睡事件", "Sleepy events");
    m_comboAllDayType.InsertString(nIndex, szLan);
    m_comboAllDayType.SetItemData(nIndex, 34);
    m_comboTimeRecType1.InsertString(nIndex, szLan);
    m_comboTimeRecType1.SetItemData(nIndex, 34);
    m_comboTimeRecType2.InsertString(nIndex, szLan);
    m_comboTimeRecType2.SetItemData(nIndex, 34);
    m_comboTimeRecType3.InsertString(nIndex, szLan);
    m_comboTimeRecType3.SetItemData(nIndex, 34);
    m_comboTimeRecType4.InsertString(nIndex, szLan);
    m_comboTimeRecType4.SetItemData(nIndex, 34);
    m_comboTimeRecType5.InsertString(nIndex, szLan);
    m_comboTimeRecType5.SetItemData(nIndex, 34);
    m_comboTimeRecType6.InsertString(nIndex, szLan);
    m_comboTimeRecType6.SetItemData(nIndex, 34);
    m_comboTimeRecType7.InsertString(nIndex, szLan);
    m_comboTimeRecType7.SetItemData(nIndex, 34);
    m_comboTimeRecType8.InsertString(nIndex, szLan);
    m_comboTimeRecType8.SetItemData(nIndex, 34);
    nIndex++;

    g_StringLanType(szLan, "船只检测", "Ships detection");
    m_comboAllDayType.InsertString(nIndex, szLan);
    m_comboAllDayType.SetItemData(nIndex, 35);
    m_comboTimeRecType1.InsertString(nIndex, szLan);
    m_comboTimeRecType1.SetItemData(nIndex, 35);
    m_comboTimeRecType2.InsertString(nIndex, szLan);
    m_comboTimeRecType2.SetItemData(nIndex, 35);
    m_comboTimeRecType3.InsertString(nIndex, szLan);
    m_comboTimeRecType3.SetItemData(nIndex, 35);
    m_comboTimeRecType4.InsertString(nIndex, szLan);
    m_comboTimeRecType4.SetItemData(nIndex, 35);
    m_comboTimeRecType5.InsertString(nIndex, szLan);
    m_comboTimeRecType5.SetItemData(nIndex, 35);
    m_comboTimeRecType6.InsertString(nIndex, szLan);
    m_comboTimeRecType6.SetItemData(nIndex, 35);
    m_comboTimeRecType7.InsertString(nIndex, szLan);
    m_comboTimeRecType7.SetItemData(nIndex, 35);
    m_comboTimeRecType8.InsertString(nIndex, szLan);
    m_comboTimeRecType8.SetItemData(nIndex, 35);
    nIndex++;

    g_StringLanType(szLan, "测温预警", "Temperature Warning");
    m_comboAllDayType.InsertString(nIndex, szLan);
    m_comboAllDayType.SetItemData(nIndex, 36);
    m_comboTimeRecType1.InsertString(nIndex, szLan);
    m_comboTimeRecType1.SetItemData(nIndex, 36);
    m_comboTimeRecType2.InsertString(nIndex, szLan);
    m_comboTimeRecType2.SetItemData(nIndex, 36);
    m_comboTimeRecType3.InsertString(nIndex, szLan);
    m_comboTimeRecType3.SetItemData(nIndex, 36);
    m_comboTimeRecType4.InsertString(nIndex, szLan);
    m_comboTimeRecType4.SetItemData(nIndex, 36);
    m_comboTimeRecType5.InsertString(nIndex, szLan);
    m_comboTimeRecType5.SetItemData(nIndex, 36);
    m_comboTimeRecType6.InsertString(nIndex, szLan);
    m_comboTimeRecType6.SetItemData(nIndex, 36);
    m_comboTimeRecType7.InsertString(nIndex, szLan);
    m_comboTimeRecType7.SetItemData(nIndex, 36);
    m_comboTimeRecType8.InsertString(nIndex, szLan);
    m_comboTimeRecType8.SetItemData(nIndex, 36);
    nIndex++;

    g_StringLanType(szLan, "测温报警", "Temperature Alarm");
    m_comboAllDayType.InsertString(nIndex, szLan);
    m_comboAllDayType.SetItemData(nIndex, 37);
    m_comboTimeRecType1.InsertString(nIndex, szLan);
    m_comboTimeRecType1.SetItemData(nIndex, 37);
    m_comboTimeRecType2.InsertString(nIndex, szLan);
    m_comboTimeRecType2.SetItemData(nIndex, 37);
    m_comboTimeRecType3.InsertString(nIndex, szLan);
    m_comboTimeRecType3.SetItemData(nIndex, 37);
    m_comboTimeRecType4.InsertString(nIndex, szLan);
    m_comboTimeRecType4.SetItemData(nIndex, 37);
    m_comboTimeRecType5.InsertString(nIndex, szLan);
    m_comboTimeRecType5.SetItemData(nIndex, 37);
    m_comboTimeRecType6.InsertString(nIndex, szLan);
    m_comboTimeRecType6.SetItemData(nIndex, 37);
    m_comboTimeRecType7.InsertString(nIndex, szLan);
    m_comboTimeRecType7.SetItemData(nIndex, 37);
    m_comboTimeRecType8.InsertString(nIndex, szLan);
    m_comboTimeRecType8.SetItemData(nIndex, 37);
    nIndex++;

	g_StringLanType(szLan, "温差报警", "Temperature Diff Alarm");
	m_comboAllDayType.InsertString(nIndex, szLan);
	m_comboAllDayType.SetItemData(nIndex, 38);
	m_comboTimeRecType1.InsertString(nIndex, szLan);
	m_comboTimeRecType1.SetItemData(nIndex, 38);
	m_comboTimeRecType2.InsertString(nIndex, szLan);
	m_comboTimeRecType2.SetItemData(nIndex, 38);
	m_comboTimeRecType3.InsertString(nIndex, szLan);
	m_comboTimeRecType3.SetItemData(nIndex, 38);
	m_comboTimeRecType4.InsertString(nIndex, szLan);
	m_comboTimeRecType4.SetItemData(nIndex, 38);
	m_comboTimeRecType5.InsertString(nIndex, szLan);
	m_comboTimeRecType5.SetItemData(nIndex, 38);
	m_comboTimeRecType6.InsertString(nIndex, szLan);
	m_comboTimeRecType6.SetItemData(nIndex, 38);
	m_comboTimeRecType7.InsertString(nIndex, szLan);
	m_comboTimeRecType7.SetItemData(nIndex, 38);
	m_comboTimeRecType8.InsertString(nIndex, szLan);
	m_comboTimeRecType8.SetItemData(nIndex, 38);
	nIndex++;
    g_StringLanType(szLan, "离线测温报警", "Temperature Offline Alarm");
    m_comboAllDayType.InsertString(nIndex, szLan);
    m_comboAllDayType.SetItemData(nIndex, 39);
    m_comboTimeRecType1.InsertString(nIndex, szLan);
    m_comboTimeRecType1.SetItemData(nIndex, 39);
    m_comboTimeRecType2.InsertString(nIndex, szLan);
    m_comboTimeRecType2.SetItemData(nIndex, 39);
    m_comboTimeRecType3.InsertString(nIndex, szLan);
    m_comboTimeRecType3.SetItemData(nIndex, 39);
    m_comboTimeRecType4.InsertString(nIndex, szLan);
    m_comboTimeRecType4.SetItemData(nIndex, 39);
    m_comboTimeRecType5.InsertString(nIndex, szLan);
    m_comboTimeRecType5.SetItemData(nIndex, 39);
    m_comboTimeRecType6.InsertString(nIndex, szLan);
    m_comboTimeRecType6.SetItemData(nIndex, 39);
    m_comboTimeRecType7.InsertString(nIndex, szLan);
    m_comboTimeRecType7.SetItemData(nIndex, 39);
    m_comboTimeRecType8.InsertString(nIndex, szLan);
    m_comboTimeRecType8.SetItemData(nIndex, 39);
    nIndex++;

    g_StringLanType(szLan, "防区报警", "AlarmIn Alarm");
    m_comboAllDayType.InsertString(nIndex, szLan);
    m_comboAllDayType.SetItemData(nIndex, 40);
    m_comboTimeRecType1.InsertString(nIndex, szLan);
    m_comboTimeRecType1.SetItemData(nIndex, 40);
    m_comboTimeRecType2.InsertString(nIndex, szLan);
    m_comboTimeRecType2.SetItemData(nIndex, 40);
    m_comboTimeRecType3.InsertString(nIndex, szLan);
    m_comboTimeRecType3.SetItemData(nIndex, 40);
    m_comboTimeRecType4.InsertString(nIndex, szLan);
    m_comboTimeRecType4.SetItemData(nIndex, 40);
    m_comboTimeRecType5.InsertString(nIndex, szLan);
    m_comboTimeRecType5.SetItemData(nIndex, 40);
    m_comboTimeRecType6.InsertString(nIndex, szLan);
    m_comboTimeRecType6.SetItemData(nIndex, 40);
    m_comboTimeRecType7.InsertString(nIndex, szLan);
    m_comboTimeRecType7.SetItemData(nIndex, 40);
    m_comboTimeRecType8.InsertString(nIndex, szLan);
    m_comboTimeRecType8.SetItemData(nIndex, 40);
    nIndex++;

    g_StringLanType(szLan, "紧急求助", "Emergency Call Help Alarm");
    m_comboAllDayType.InsertString(nIndex, szLan);
    m_comboAllDayType.SetItemData(nIndex, 41);
    m_comboTimeRecType1.InsertString(nIndex, szLan);
    m_comboTimeRecType1.SetItemData(nIndex, 41);
    m_comboTimeRecType2.InsertString(nIndex, szLan);
    m_comboTimeRecType2.SetItemData(nIndex, 41);
    m_comboTimeRecType3.InsertString(nIndex, szLan);
    m_comboTimeRecType3.SetItemData(nIndex, 41);
    m_comboTimeRecType4.InsertString(nIndex, szLan);
    m_comboTimeRecType4.SetItemData(nIndex, 41);
    m_comboTimeRecType5.InsertString(nIndex, szLan);
    m_comboTimeRecType5.SetItemData(nIndex, 41);
    m_comboTimeRecType6.InsertString(nIndex, szLan);
    m_comboTimeRecType6.SetItemData(nIndex, 41);
    m_comboTimeRecType7.InsertString(nIndex, szLan);
    m_comboTimeRecType7.SetItemData(nIndex, 41);
    m_comboTimeRecType8.InsertString(nIndex, szLan);
    m_comboTimeRecType8.SetItemData(nIndex, 41);
    nIndex++;

    g_StringLanType(szLan, "业务咨询", "Consult");
    m_comboAllDayType.InsertString(nIndex, szLan);
    m_comboAllDayType.SetItemData(nIndex, 42);
    m_comboTimeRecType1.InsertString(nIndex, szLan);
    m_comboTimeRecType1.SetItemData(nIndex, 42);
    m_comboTimeRecType2.InsertString(nIndex, szLan);
    m_comboTimeRecType2.SetItemData(nIndex, 42);
    m_comboTimeRecType3.InsertString(nIndex, szLan);
    m_comboTimeRecType3.SetItemData(nIndex, 42);
    m_comboTimeRecType4.InsertString(nIndex, szLan);
    m_comboTimeRecType4.SetItemData(nIndex, 42);
    m_comboTimeRecType5.InsertString(nIndex, szLan);
    m_comboTimeRecType5.SetItemData(nIndex, 42);
    m_comboTimeRecType6.InsertString(nIndex, szLan);
    m_comboTimeRecType6.SetItemData(nIndex, 42);
    m_comboTimeRecType7.InsertString(nIndex, szLan);
    m_comboTimeRecType7.SetItemData(nIndex, 42);
    m_comboTimeRecType8.InsertString(nIndex, szLan);
    m_comboTimeRecType8.SetItemData(nIndex, 42);
    nIndex++;

    g_StringLanType(szLan, "起身检测", "GetUp");
    m_comboAllDayType.InsertString(nIndex, szLan);
    m_comboAllDayType.SetItemData(nIndex, 43);
    m_comboTimeRecType1.InsertString(nIndex, szLan);
    m_comboTimeRecType1.SetItemData(nIndex, 43);
    m_comboTimeRecType2.InsertString(nIndex, szLan);
    m_comboTimeRecType2.SetItemData(nIndex, 43);
    m_comboTimeRecType3.InsertString(nIndex, szLan);
    m_comboTimeRecType3.SetItemData(nIndex, 43);
    m_comboTimeRecType4.InsertString(nIndex, szLan);
    m_comboTimeRecType4.SetItemData(nIndex, 43);
    m_comboTimeRecType5.InsertString(nIndex, szLan);
    m_comboTimeRecType5.SetItemData(nIndex, 43);
    m_comboTimeRecType6.InsertString(nIndex, szLan);
    m_comboTimeRecType6.SetItemData(nIndex, 43);
    m_comboTimeRecType7.InsertString(nIndex, szLan);
    m_comboTimeRecType7.SetItemData(nIndex, 43);
    m_comboTimeRecType8.InsertString(nIndex, szLan);
    m_comboTimeRecType8.SetItemData(nIndex, 43);
    nIndex++;


    g_StringLanType(szLan, "折线攀高", "AdvReachHeight");
    m_comboAllDayType.InsertString(nIndex, szLan);
    m_comboAllDayType.SetItemData(nIndex, 44);
    m_comboTimeRecType1.InsertString(nIndex, szLan);
    m_comboTimeRecType1.SetItemData(nIndex, 44);
    m_comboTimeRecType2.InsertString(nIndex, szLan);
    m_comboTimeRecType2.SetItemData(nIndex, 44);
    m_comboTimeRecType3.InsertString(nIndex, szLan);
    m_comboTimeRecType3.SetItemData(nIndex, 44);
    m_comboTimeRecType4.InsertString(nIndex, szLan);
    m_comboTimeRecType4.SetItemData(nIndex, 44);
    m_comboTimeRecType5.InsertString(nIndex, szLan);
    m_comboTimeRecType5.SetItemData(nIndex, 44);
    m_comboTimeRecType6.InsertString(nIndex, szLan);
    m_comboTimeRecType6.SetItemData(nIndex, 44);
    m_comboTimeRecType7.InsertString(nIndex, szLan);
    m_comboTimeRecType7.SetItemData(nIndex, 44);
    m_comboTimeRecType8.InsertString(nIndex, szLan);
    m_comboTimeRecType8.SetItemData(nIndex, 44);
    nIndex++;


    g_StringLanType(szLan, "如厕超时", "ToiletTarry");
    m_comboAllDayType.InsertString(nIndex, szLan);
    m_comboAllDayType.SetItemData(nIndex, 45);
    m_comboTimeRecType1.InsertString(nIndex, szLan);
    m_comboTimeRecType1.SetItemData(nIndex, 45);
    m_comboTimeRecType2.InsertString(nIndex, szLan);
    m_comboTimeRecType2.SetItemData(nIndex, 45);
    m_comboTimeRecType3.InsertString(nIndex, szLan);
    m_comboTimeRecType3.SetItemData(nIndex, 45);
    m_comboTimeRecType4.InsertString(nIndex, szLan);
    m_comboTimeRecType4.SetItemData(nIndex, 45);
    m_comboTimeRecType5.InsertString(nIndex, szLan);
    m_comboTimeRecType5.SetItemData(nIndex, 45);
    m_comboTimeRecType6.InsertString(nIndex, szLan);
    m_comboTimeRecType6.SetItemData(nIndex, 45);
    m_comboTimeRecType7.InsertString(nIndex, szLan);
    m_comboTimeRecType7.SetItemData(nIndex, 45);
    m_comboTimeRecType8.InsertString(nIndex, szLan);
    m_comboTimeRecType8.SetItemData(nIndex, 45);
    nIndex++;


    g_StringLanType(szLan, "目标抓拍", "FaceSnap");
    m_comboAllDayType.InsertString(nIndex, szLan);
    m_comboAllDayType.SetItemData(nIndex, 46);
    m_comboTimeRecType1.InsertString(nIndex, szLan);
    m_comboTimeRecType1.SetItemData(nIndex, 46);
    m_comboTimeRecType2.InsertString(nIndex, szLan);
    m_comboTimeRecType2.SetItemData(nIndex, 46);
    m_comboTimeRecType3.InsertString(nIndex, szLan);
    m_comboTimeRecType3.SetItemData(nIndex, 46);
    m_comboTimeRecType4.InsertString(nIndex, szLan);
    m_comboTimeRecType4.SetItemData(nIndex, 46);
    m_comboTimeRecType5.InsertString(nIndex, szLan);
    m_comboTimeRecType5.SetItemData(nIndex, 46);
    m_comboTimeRecType6.InsertString(nIndex, szLan);
    m_comboTimeRecType6.SetItemData(nIndex, 46);
    m_comboTimeRecType7.InsertString(nIndex, szLan);
    m_comboTimeRecType7.SetItemData(nIndex, 46);
    m_comboTimeRecType8.InsertString(nIndex, szLan);
    m_comboTimeRecType8.SetItemData(nIndex, 46);
    nIndex++;

    g_StringLanType(szLan, "非法摆摊", "UnregisteredStreetVendor");
    m_comboAllDayType.InsertString(nIndex, szLan);
    m_comboAllDayType.SetItemData(nIndex, 47);
    m_comboTimeRecType1.InsertString(nIndex, szLan);
    m_comboTimeRecType1.SetItemData(nIndex, 47);
    m_comboTimeRecType2.InsertString(nIndex, szLan);
    m_comboTimeRecType2.SetItemData(nIndex, 47);
    m_comboTimeRecType3.InsertString(nIndex, szLan);
    m_comboTimeRecType3.SetItemData(nIndex, 47);
    m_comboTimeRecType4.InsertString(nIndex, szLan);
    m_comboTimeRecType4.SetItemData(nIndex, 47);
    m_comboTimeRecType5.InsertString(nIndex, szLan);
    m_comboTimeRecType5.SetItemData(nIndex, 47);
    m_comboTimeRecType6.InsertString(nIndex, szLan);
    m_comboTimeRecType6.SetItemData(nIndex, 47);
    m_comboTimeRecType7.InsertString(nIndex, szLan);
    m_comboTimeRecType7.SetItemData(nIndex, 47);
    m_comboTimeRecType8.InsertString(nIndex, szLan);
    m_comboTimeRecType8.SetItemData(nIndex, 47);
    nIndex++;

    g_StringLanType(szLan, "目标识别", "humanRecognition");
    m_comboAllDayType.InsertString(nIndex, szLan);
    m_comboAllDayType.SetItemData(nIndex, 48);
    m_comboTimeRecType1.InsertString(nIndex, szLan);
    m_comboTimeRecType1.SetItemData(nIndex, 48);
    m_comboTimeRecType2.InsertString(nIndex, szLan);
    m_comboTimeRecType2.SetItemData(nIndex, 48);
    m_comboTimeRecType3.InsertString(nIndex, szLan);
    m_comboTimeRecType3.SetItemData(nIndex, 48);
    m_comboTimeRecType4.InsertString(nIndex, szLan);
    m_comboTimeRecType4.SetItemData(nIndex, 48);
    m_comboTimeRecType5.InsertString(nIndex, szLan);
    m_comboTimeRecType5.SetItemData(nIndex, 48);
    m_comboTimeRecType6.InsertString(nIndex, szLan);
    m_comboTimeRecType6.SetItemData(nIndex, 48);
    m_comboTimeRecType7.InsertString(nIndex, szLan);
    m_comboTimeRecType7.SetItemData(nIndex, 48);
    m_comboTimeRecType8.InsertString(nIndex, szLan);
    m_comboTimeRecType8.SetItemData(nIndex, 48);
    nIndex++;

    g_StringLanType(szLan, "剧烈运动", "violentMotion");
    m_comboAllDayType.InsertString(nIndex, szLan);
    m_comboAllDayType.SetItemData(nIndex, 49);
    m_comboTimeRecType1.InsertString(nIndex, szLan);
    m_comboTimeRecType1.SetItemData(nIndex, 49);
    m_comboTimeRecType2.InsertString(nIndex, szLan);
    m_comboTimeRecType2.SetItemData(nIndex, 49);
    m_comboTimeRecType3.InsertString(nIndex, szLan);
    m_comboTimeRecType3.SetItemData(nIndex, 49);
    m_comboTimeRecType4.InsertString(nIndex, szLan);
    m_comboTimeRecType4.SetItemData(nIndex, 49);
    m_comboTimeRecType5.InsertString(nIndex, szLan);
    m_comboTimeRecType5.SetItemData(nIndex, 49);
    m_comboTimeRecType6.InsertString(nIndex, szLan);
    m_comboTimeRecType6.SetItemData(nIndex, 49);
    m_comboTimeRecType7.InsertString(nIndex, szLan);
    m_comboTimeRecType7.SetItemData(nIndex, 49);
    m_comboTimeRecType8.InsertString(nIndex, szLan);
    m_comboTimeRecType8.SetItemData(nIndex, 49);
    nIndex++;

    g_StringLanType(szLan, "离岗检测", "leaveBehavior");
    m_comboAllDayType.InsertString(nIndex, szLan);
    m_comboAllDayType.SetItemData(nIndex, 50);
    m_comboTimeRecType1.InsertString(nIndex, szLan);
    m_comboTimeRecType1.SetItemData(nIndex, 50);
    m_comboTimeRecType2.InsertString(nIndex, szLan);
    m_comboTimeRecType2.SetItemData(nIndex, 50);
    m_comboTimeRecType3.InsertString(nIndex, szLan);
    m_comboTimeRecType3.SetItemData(nIndex, 50);
    m_comboTimeRecType4.InsertString(nIndex, szLan);
    m_comboTimeRecType4.SetItemData(nIndex, 50);
    m_comboTimeRecType5.InsertString(nIndex, szLan);
    m_comboTimeRecType5.SetItemData(nIndex, 50);
    m_comboTimeRecType6.InsertString(nIndex, szLan);
    m_comboTimeRecType6.SetItemData(nIndex, 50);
    m_comboTimeRecType7.InsertString(nIndex, szLan);
    m_comboTimeRecType7.SetItemData(nIndex, 50);
    m_comboTimeRecType8.InsertString(nIndex, szLan);
    m_comboTimeRecType8.SetItemData(nIndex, 50);
    nIndex++;

    g_StringLanType(szLan, "起立", "standUp");
    m_comboAllDayType.InsertString(nIndex, szLan);
    m_comboAllDayType.SetItemData(nIndex, 51);
    m_comboTimeRecType1.InsertString(nIndex, szLan);
    m_comboTimeRecType1.SetItemData(nIndex, 51);
    m_comboTimeRecType2.InsertString(nIndex, szLan);
    m_comboTimeRecType2.SetItemData(nIndex, 51);
    m_comboTimeRecType3.InsertString(nIndex, szLan);
    m_comboTimeRecType3.SetItemData(nIndex, 51);
    m_comboTimeRecType4.InsertString(nIndex, szLan);
    m_comboTimeRecType4.SetItemData(nIndex, 51);
    m_comboTimeRecType5.InsertString(nIndex, szLan);
    m_comboTimeRecType5.SetItemData(nIndex, 51);
    m_comboTimeRecType6.InsertString(nIndex, szLan);
    m_comboTimeRecType6.SetItemData(nIndex, 51);
    m_comboTimeRecType7.InsertString(nIndex, szLan);
    m_comboTimeRecType7.SetItemData(nIndex, 51);
    m_comboTimeRecType8.InsertString(nIndex, szLan);
    m_comboTimeRecType8.SetItemData(nIndex, 51);
    nIndex++;

    g_StringLanType(szLan, "人数变化", "peopleNumChange");
    m_comboAllDayType.InsertString(nIndex, szLan);
    m_comboAllDayType.SetItemData(nIndex, 52);
    m_comboTimeRecType1.InsertString(nIndex, szLan);
    m_comboTimeRecType1.SetItemData(nIndex, 52);
    m_comboTimeRecType2.InsertString(nIndex, szLan);
    m_comboTimeRecType2.SetItemData(nIndex, 52);
    m_comboTimeRecType3.InsertString(nIndex, szLan);
    m_comboTimeRecType3.SetItemData(nIndex, 52);
    m_comboTimeRecType4.InsertString(nIndex, szLan);
    m_comboTimeRecType4.SetItemData(nIndex, 52);
    m_comboTimeRecType5.InsertString(nIndex, szLan);
    m_comboTimeRecType5.SetItemData(nIndex, 52);
    m_comboTimeRecType6.InsertString(nIndex, szLan);
    m_comboTimeRecType6.SetItemData(nIndex, 52);
    m_comboTimeRecType7.InsertString(nIndex, szLan);
    m_comboTimeRecType7.SetItemData(nIndex, 52);
    m_comboTimeRecType8.InsertString(nIndex, szLan);
    m_comboTimeRecType8.SetItemData(nIndex, 52);
    nIndex++;

    g_StringLanType(szLan, "废气排放监测", "wasteGas");
    m_comboAllDayType.InsertString(nIndex, szLan);
    m_comboAllDayType.SetItemData(nIndex, 53);
    m_comboTimeRecType1.InsertString(nIndex, szLan);
    m_comboTimeRecType1.SetItemData(nIndex, 53);
    m_comboTimeRecType2.InsertString(nIndex, szLan);
    m_comboTimeRecType2.SetItemData(nIndex, 53);
    m_comboTimeRecType3.InsertString(nIndex, szLan);
    m_comboTimeRecType3.SetItemData(nIndex, 53);
    m_comboTimeRecType4.InsertString(nIndex, szLan);
    m_comboTimeRecType4.SetItemData(nIndex, 53);
    m_comboTimeRecType5.InsertString(nIndex, szLan);
    m_comboTimeRecType5.SetItemData(nIndex, 53);
    m_comboTimeRecType6.InsertString(nIndex, szLan);
    m_comboTimeRecType6.SetItemData(nIndex, 53);
    m_comboTimeRecType7.InsertString(nIndex, szLan);
    m_comboTimeRecType7.SetItemData(nIndex, 53);
    m_comboTimeRecType8.InsertString(nIndex, szLan);
    m_comboTimeRecType8.SetItemData(nIndex, 53);
    nIndex++;

    g_StringLanType(szLan, "灰度报警", "greyScaleAlarms");
    m_comboAllDayType.InsertString(nIndex, szLan);
    m_comboAllDayType.SetItemData(nIndex, 54);
    m_comboTimeRecType1.InsertString(nIndex, szLan);
    m_comboTimeRecType1.SetItemData(nIndex, 54);
    m_comboTimeRecType2.InsertString(nIndex, szLan);
    m_comboTimeRecType2.SetItemData(nIndex, 54);
    m_comboTimeRecType3.InsertString(nIndex, szLan);
    m_comboTimeRecType3.SetItemData(nIndex, 54);
    m_comboTimeRecType4.InsertString(nIndex, szLan);
    m_comboTimeRecType4.SetItemData(nIndex, 54);
    m_comboTimeRecType5.InsertString(nIndex, szLan);
    m_comboTimeRecType5.SetItemData(nIndex, 54);
    m_comboTimeRecType6.InsertString(nIndex, szLan);
    m_comboTimeRecType6.SetItemData(nIndex, 54);
    m_comboTimeRecType7.InsertString(nIndex, szLan);
    m_comboTimeRecType7.SetItemData(nIndex, 54);
    m_comboTimeRecType8.InsertString(nIndex, szLan);
    m_comboTimeRecType8.SetItemData(nIndex, 54);
    nIndex++;

	m_nDate = 0;
	m_comboWeekday.SetCurSel(m_nDate);
	m_nCopyDate = 0;
	m_comboCopyWeekday.SetCurSel(m_nCopyDate);
	m_bCheckAllDay = m_struRemoteRecSchedule->struRecAllDay[m_nDate].wAllDayRecord;
	for (i=0; i<m_comboAllDayType.GetCount(); i++)
	{
		if (m_struRemoteRecSchedule->struRecAllDay[m_nDate].byRecordType == m_comboAllDayType.GetItemData(i))
		{
			m_comboAllDayType.SetCurSel(i);
		}
	}
	for (i=0; i<m_comboTimeRecType1.GetCount(); i++)
	{
		if (m_struRemoteRecSchedule->struRecordSched[m_nDate][0].byRecordType == m_comboTimeRecType1.GetItemData(i))
		{
			m_comboTimeRecType1.SetCurSel(i);
		}
	}
	for (i=0; i<m_comboTimeRecType2.GetCount(); i++)
	{
		if (m_struRemoteRecSchedule->struRecordSched[m_nDate][1].byRecordType == m_comboTimeRecType2.GetItemData(i))
		{
			m_comboTimeRecType2.SetCurSel(i);
		}
	}
	for (i=0; i<m_comboTimeRecType3.GetCount(); i++)
	{
		if (m_struRemoteRecSchedule->struRecordSched[m_nDate][2].byRecordType == m_comboTimeRecType3.GetItemData(i))
		{
			m_comboTimeRecType3.SetCurSel(i);
		}
	}
	for (i=0; i<m_comboTimeRecType4.GetCount(); i++)
	{
		if (m_struRemoteRecSchedule->struRecordSched[m_nDate][3].byRecordType == m_comboTimeRecType4.GetItemData(i))
		{
			m_comboTimeRecType4.SetCurSel(i);
		}
	}
	for (i=0; i<m_comboTimeRecType5.GetCount(); i++)
	{
		if (m_struRemoteRecSchedule->struRecordSched[m_nDate][4].byRecordType == m_comboTimeRecType5.GetItemData(i))
		{
			m_comboTimeRecType5.SetCurSel(i);
		}
	}
	for (i=0; i<m_comboTimeRecType6.GetCount(); i++)
	{
		if (m_struRemoteRecSchedule->struRecordSched[m_nDate][5].byRecordType == m_comboTimeRecType6.GetItemData(i))
		{
			m_comboTimeRecType6.SetCurSel(i);
		}
	}
	for (i=0; i<m_comboTimeRecType7.GetCount(); i++)
	{
		if (m_struRemoteRecSchedule->struRecordSched[m_nDate][6].byRecordType == m_comboTimeRecType7.GetItemData(i))
		{
			m_comboTimeRecType7.SetCurSel(i);
		}
	}
	for (i=0; i<m_comboTimeRecType8.GetCount(); i++)
	{
		if (m_struRemoteRecSchedule->struRecordSched[m_nDate][7].byRecordType == m_comboTimeRecType8.GetItemData(i))
		{
			m_comboTimeRecType8.SetCurSel(i);
		}
	}
// 	m_comboAllDayType.SetCurSel(m_struRemoteRecSchedule->struRecAllDay[m_nDate].byRecordType);		
// 	m_comboTimeRecType1.SetCurSel(m_struRemoteRecSchedule->struRecordSched[m_nDate][0].byRecordType);
// 	m_comboTimeRecType2.SetCurSel(m_struRemoteRecSchedule->struRecordSched[m_nDate][1].byRecordType);
// 	m_comboTimeRecType3.SetCurSel(m_struRemoteRecSchedule->struRecordSched[m_nDate][2].byRecordType);
// 	m_comboTimeRecType4.SetCurSel(m_struRemoteRecSchedule->struRecordSched[m_nDate][3].byRecordType);
// 	m_comboTimeRecType5.SetCurSel(m_struRemoteRecSchedule->struRecordSched[m_nDate][4].byRecordType);
// 	m_comboTimeRecType6.SetCurSel(m_struRemoteRecSchedule->struRecordSched[m_nDate][5].byRecordType);
// 	m_comboTimeRecType7.SetCurSel(m_struRemoteRecSchedule->struRecordSched[m_nDate][6].byRecordType);
// 	m_comboTimeRecType8.SetCurSel(m_struRemoteRecSchedule->struRecordSched[m_nDate][7].byRecordType);

	m_iHour11 = m_struRemoteRecSchedule->struRecordSched[m_nDate][0].struRecordTime.byStartHour;
	m_iHour12 = m_struRemoteRecSchedule->struRecordSched[m_nDate][0].struRecordTime.byStopHour;
	m_iHour21 = m_struRemoteRecSchedule->struRecordSched[m_nDate][1].struRecordTime.byStartHour;
	m_iHour22 = m_struRemoteRecSchedule->struRecordSched[m_nDate][1].struRecordTime.byStopHour;
	m_iHour31 = m_struRemoteRecSchedule->struRecordSched[m_nDate][2].struRecordTime.byStartHour;
	m_iHour32 = m_struRemoteRecSchedule->struRecordSched[m_nDate][2].struRecordTime.byStopHour;
	m_iHour41 = m_struRemoteRecSchedule->struRecordSched[m_nDate][3].struRecordTime.byStartHour;
	m_iHour42 = m_struRemoteRecSchedule->struRecordSched[m_nDate][3].struRecordTime.byStopHour;
	m_iMin11 = m_struRemoteRecSchedule->struRecordSched[m_nDate][0].struRecordTime.byStartMin;
	m_iMin12 = m_struRemoteRecSchedule->struRecordSched[m_nDate][0].struRecordTime.byStopMin;
	m_iMin21 = m_struRemoteRecSchedule->struRecordSched[m_nDate][1].struRecordTime.byStartMin;
	m_iMin22 = m_struRemoteRecSchedule->struRecordSched[m_nDate][1].struRecordTime.byStopMin;
	m_iMin31 = m_struRemoteRecSchedule->struRecordSched[m_nDate][2].struRecordTime.byStartMin;
	m_iMin32 = m_struRemoteRecSchedule->struRecordSched[m_nDate][2].struRecordTime.byStopMin;
	m_iMin41 = m_struRemoteRecSchedule->struRecordSched[m_nDate][3].struRecordTime.byStartMin;
	m_iMin42 = m_struRemoteRecSchedule->struRecordSched[m_nDate][3].struRecordTime.byStopMin;

	m_iHour51 = m_struRemoteRecSchedule->struRecordSched[m_nDate][4].struRecordTime.byStartHour;
	m_iHour52 = m_struRemoteRecSchedule->struRecordSched[m_nDate][4].struRecordTime.byStopHour;
	m_iHour61 = m_struRemoteRecSchedule->struRecordSched[m_nDate][5].struRecordTime.byStartHour;
	m_iHour62 = m_struRemoteRecSchedule->struRecordSched[m_nDate][5].struRecordTime.byStopHour;
	m_iHour71 = m_struRemoteRecSchedule->struRecordSched[m_nDate][6].struRecordTime.byStartHour;
	m_iHour72 = m_struRemoteRecSchedule->struRecordSched[m_nDate][6].struRecordTime.byStopHour;
	m_iHour81 = m_struRemoteRecSchedule->struRecordSched[m_nDate][7].struRecordTime.byStartHour;
	m_iHour82 = m_struRemoteRecSchedule->struRecordSched[m_nDate][7].struRecordTime.byStopHour;
	m_iMin51 = m_struRemoteRecSchedule->struRecordSched[m_nDate][4].struRecordTime.byStartMin;
	m_iMin52 = m_struRemoteRecSchedule->struRecordSched[m_nDate][4].struRecordTime.byStopMin;
	m_iMin61 = m_struRemoteRecSchedule->struRecordSched[m_nDate][5].struRecordTime.byStartMin;
	m_iMin62 = m_struRemoteRecSchedule->struRecordSched[m_nDate][5].struRecordTime.byStopMin;
	m_iMin71 = m_struRemoteRecSchedule->struRecordSched[m_nDate][6].struRecordTime.byStartMin;
	m_iMin72 = m_struRemoteRecSchedule->struRecordSched[m_nDate][6].struRecordTime.byStopMin;
	m_iMin81 = m_struRemoteRecSchedule->struRecordSched[m_nDate][7].struRecordTime.byStartMin;
	m_iMin82 = m_struRemoteRecSchedule->struRecordSched[m_nDate][7].struRecordTime.byStopMin;
	EnableControl(!m_bCheckAllDay);
	UpdateData(FALSE);

	return TRUE;  // return TRUE unless you set the focus to a control
	// EXCEPTION: OCX Property Pages should return FALSE
}

/*********************************************************
Function:	EnableControl
Desc:		Dialog control enable
Input:	
Output:	
Return:	
**********************************************************/
void CDlgRemoteRecordSchedule::EnableControl(BOOL bEnable)
{
	GetDlgItem(IDC_EDIT_HOUR11)->EnableWindow(bEnable);
	GetDlgItem(IDC_EDIT_HOUR21)->EnableWindow(bEnable);
	GetDlgItem(IDC_EDIT_HOUR31)->EnableWindow(bEnable);
	GetDlgItem(IDC_EDIT_HOUR41)->EnableWindow(bEnable);
	GetDlgItem(IDC_EDIT_HOUR51)->EnableWindow(bEnable);
	GetDlgItem(IDC_EDIT_HOUR61)->EnableWindow(bEnable);
	GetDlgItem(IDC_EDIT_HOUR71)->EnableWindow(bEnable);
	GetDlgItem(IDC_EDIT_HOUR81)->EnableWindow(bEnable);

	GetDlgItem(IDC_EDIT_MIN11)->EnableWindow(bEnable);
	GetDlgItem(IDC_EDIT_MIN21)->EnableWindow(bEnable);
	GetDlgItem(IDC_EDIT_MIN31)->EnableWindow(bEnable);
	GetDlgItem(IDC_EDIT_MIN41)->EnableWindow(bEnable);
	GetDlgItem(IDC_EDIT_MIN51)->EnableWindow(bEnable);
	GetDlgItem(IDC_EDIT_MIN61)->EnableWindow(bEnable);
	GetDlgItem(IDC_EDIT_MIN71)->EnableWindow(bEnable);
	GetDlgItem(IDC_EDIT_MIN81)->EnableWindow(bEnable);

	GetDlgItem(IDC_EDIT_HOUR12)->EnableWindow(bEnable);
	GetDlgItem(IDC_EDIT_HOUR22)->EnableWindow(bEnable);
	GetDlgItem(IDC_EDIT_HOUR32)->EnableWindow(bEnable);
	GetDlgItem(IDC_EDIT_HOUR42)->EnableWindow(bEnable);
	GetDlgItem(IDC_EDIT_HOUR52)->EnableWindow(bEnable);
	GetDlgItem(IDC_EDIT_HOUR62)->EnableWindow(bEnable);
	GetDlgItem(IDC_EDIT_HOUR72)->EnableWindow(bEnable);
	GetDlgItem(IDC_EDIT_HOUR82)->EnableWindow(bEnable);

	GetDlgItem(IDC_EDIT_MIN12)->EnableWindow(bEnable);
	GetDlgItem(IDC_EDIT_MIN22)->EnableWindow(bEnable);
	GetDlgItem(IDC_EDIT_MIN32)->EnableWindow(bEnable);
	GetDlgItem(IDC_EDIT_MIN42)->EnableWindow(bEnable);
	GetDlgItem(IDC_EDIT_MIN52)->EnableWindow(bEnable);
	GetDlgItem(IDC_EDIT_MIN62)->EnableWindow(bEnable);
	GetDlgItem(IDC_EDIT_MIN72)->EnableWindow(bEnable);
	GetDlgItem(IDC_EDIT_MIN82)->EnableWindow(bEnable);

	GetDlgItem(IDC_COMBO_TIME_REC_TYPE1)->EnableWindow(bEnable);
	GetDlgItem(IDC_COMBO_TIME_REC_TYPE2)->EnableWindow(bEnable);
	GetDlgItem(IDC_COMBO_TIME_REC_TYPE3)->EnableWindow(bEnable);
	GetDlgItem(IDC_COMBO_TIME_REC_TYPE4)->EnableWindow(bEnable);
	GetDlgItem(IDC_COMBO_TIME_REC_TYPE5)->EnableWindow(bEnable);
	GetDlgItem(IDC_COMBO_TIME_REC_TYPE6)->EnableWindow(bEnable);
	GetDlgItem(IDC_COMBO_TIME_REC_TYPE7)->EnableWindow(bEnable);
	GetDlgItem(IDC_COMBO_TIME_REC_TYPE8)->EnableWindow(bEnable);
	GetDlgItem(IDC_COMBO_ALL_DAY_TYPE)->EnableWindow(!bEnable);
}

/*********************************************************
Function:	OnBnClickedBtnRemoteRecOk
Desc:		check and update schedule settings
Input:	
Output:	
Return:	
**********************************************************/
void CDlgRemoteRecordSchedule::OnBnClickedBtnRemoteRecOk()
{
	UpdateData(TRUE);
	if (!TimeTest())
	{
		return;
	}
    
    if (7 == m_nDate) // 假日 单独配 
    {
        m_struHolidayRecord.struRecDay.wAllDayRecord = (WORD)m_bCheckAllDay;
        if (m_bCheckAllDay)
        {		
            m_struHolidayRecord.struRecDay.byRecordType = (BYTE)m_comboAllDayType.GetItemData(m_comboAllDayType.GetCurSel());
        }
        else
        {
            
            m_struHolidayRecord.struRecordSched[0].byRecordType = (BYTE)m_comboTimeRecType1.GetItemData(m_comboTimeRecType1.GetCurSel());
            m_struHolidayRecord.struRecordSched[1].byRecordType = (BYTE)m_comboTimeRecType2.GetItemData(m_comboTimeRecType2.GetCurSel());
            m_struHolidayRecord.struRecordSched[2].byRecordType = (BYTE)m_comboTimeRecType3.GetItemData(m_comboTimeRecType3.GetCurSel());
            m_struHolidayRecord.struRecordSched[3].byRecordType = (BYTE)m_comboTimeRecType4.GetItemData(m_comboTimeRecType4.GetCurSel());	
            m_struHolidayRecord.struRecordSched[4].byRecordType = (BYTE)m_comboTimeRecType5.GetItemData(m_comboTimeRecType5.GetCurSel());
            m_struHolidayRecord.struRecordSched[5].byRecordType = (BYTE)m_comboTimeRecType6.GetItemData(m_comboTimeRecType6.GetCurSel());
            m_struHolidayRecord.struRecordSched[6].byRecordType = (BYTE)m_comboTimeRecType7.GetItemData(m_comboTimeRecType7.GetCurSel());
            m_struHolidayRecord.struRecordSched[7].byRecordType = (BYTE)m_comboTimeRecType8.GetItemData(m_comboTimeRecType8.GetCurSel());
            
            m_struHolidayRecord.struRecordSched[0].struRecordTime.byStartHour = (BYTE)m_iHour11;
            m_struHolidayRecord.struRecordSched[0].struRecordTime.byStopHour = (BYTE)m_iHour12;
            m_struHolidayRecord.struRecordSched[1].struRecordTime.byStartHour = (BYTE)m_iHour21;
            m_struHolidayRecord.struRecordSched[1].struRecordTime.byStopHour = (BYTE)m_iHour22;
            m_struHolidayRecord.struRecordSched[2].struRecordTime.byStartHour = (BYTE)m_iHour31;
            m_struHolidayRecord.struRecordSched[2].struRecordTime.byStopHour = (BYTE)m_iHour32;
            m_struHolidayRecord.struRecordSched[3].struRecordTime.byStartHour = (BYTE)m_iHour41;
            m_struHolidayRecord.struRecordSched[3].struRecordTime.byStopHour = (BYTE)m_iHour42;
            
            m_struHolidayRecord.struRecordSched[0].struRecordTime.byStartMin = (BYTE)m_iMin11;
            m_struHolidayRecord.struRecordSched[0].struRecordTime.byStopMin = (BYTE)m_iMin12;
            m_struHolidayRecord.struRecordSched[1].struRecordTime.byStartMin = (BYTE)m_iMin21;
            m_struHolidayRecord.struRecordSched[1].struRecordTime.byStopMin = (BYTE)m_iMin22;
            m_struHolidayRecord.struRecordSched[2].struRecordTime.byStartMin = (BYTE)m_iMin31;
            m_struHolidayRecord.struRecordSched[2].struRecordTime.byStopMin = (BYTE)m_iMin32;
            m_struHolidayRecord.struRecordSched[3].struRecordTime.byStartMin = (BYTE)m_iMin41;
            m_struHolidayRecord.struRecordSched[3].struRecordTime.byStopMin = (BYTE)m_iMin42;
            
            m_struHolidayRecord.struRecordSched[4].struRecordTime.byStartHour = (BYTE)m_iHour51;
            m_struHolidayRecord.struRecordSched[4].struRecordTime.byStopHour = (BYTE)m_iHour52;
            m_struHolidayRecord.struRecordSched[5].struRecordTime.byStartHour = (BYTE)m_iHour61;
            m_struHolidayRecord.struRecordSched[5].struRecordTime.byStopHour = (BYTE)m_iHour62;
            m_struHolidayRecord.struRecordSched[6].struRecordTime.byStartHour = (BYTE)m_iHour71;
            m_struHolidayRecord.struRecordSched[6].struRecordTime.byStopHour = (BYTE)m_iHour72;
            m_struHolidayRecord.struRecordSched[7].struRecordTime.byStartHour = (BYTE)m_iHour81;
            m_struHolidayRecord.struRecordSched[7].struRecordTime.byStopHour = (BYTE)m_iHour82;
            
            m_struHolidayRecord.struRecordSched[4].struRecordTime.byStartMin = (BYTE)m_iMin51;
            m_struHolidayRecord.struRecordSched[4].struRecordTime.byStopMin = (BYTE)m_iMin52;
            m_struHolidayRecord.struRecordSched[5].struRecordTime.byStartMin = (BYTE)m_iMin61;
            m_struHolidayRecord.struRecordSched[5].struRecordTime.byStopMin = (BYTE)m_iMin62;
            m_struHolidayRecord.struRecordSched[6].struRecordTime.byStartMin = (BYTE)m_iMin71;
            m_struHolidayRecord.struRecordSched[6].struRecordTime.byStopMin = (BYTE)m_iMin72;
            m_struHolidayRecord.struRecordSched[7].struRecordTime.byStartMin = (BYTE)m_iMin81;
            m_struHolidayRecord.struRecordSched[7].struRecordTime.byStopMin = (BYTE)m_iMin82;
         
        }
        if (!SetHolidayRecord(m_struHolidayRecord))
        {
            AfxMessageBox("Fail to set holiday record");
        }
    }
    else
    {
        m_struRemoteRecSchedule->struRecAllDay[m_nDate].wAllDayRecord = (WORD)m_bCheckAllDay;
        if (m_bCheckAllDay)
        {		
            m_struRemoteRecSchedule->struRecAllDay[m_nDate].byRecordType = (BYTE)m_comboAllDayType.GetItemData(m_comboAllDayType.GetCurSel());
        }
        else
        {
            m_struRemoteRecSchedule->struRecordSched[m_nDate][0].byRecordType = (BYTE)m_comboTimeRecType1.GetItemData(m_comboTimeRecType1.GetCurSel());
            m_struRemoteRecSchedule->struRecordSched[m_nDate][1].byRecordType = (BYTE)m_comboTimeRecType2.GetItemData(m_comboTimeRecType2.GetCurSel());
            m_struRemoteRecSchedule->struRecordSched[m_nDate][2].byRecordType = (BYTE)m_comboTimeRecType3.GetItemData(m_comboTimeRecType3.GetCurSel());
            m_struRemoteRecSchedule->struRecordSched[m_nDate][3].byRecordType = (BYTE)m_comboTimeRecType4.GetItemData(m_comboTimeRecType4.GetCurSel());	
            m_struRemoteRecSchedule->struRecordSched[m_nDate][4].byRecordType = (BYTE)m_comboTimeRecType5.GetItemData(m_comboTimeRecType5.GetCurSel());
            m_struRemoteRecSchedule->struRecordSched[m_nDate][5].byRecordType = (BYTE)m_comboTimeRecType6.GetItemData(m_comboTimeRecType6.GetCurSel());
            m_struRemoteRecSchedule->struRecordSched[m_nDate][6].byRecordType = (BYTE)m_comboTimeRecType7.GetItemData(m_comboTimeRecType7.GetCurSel());
            m_struRemoteRecSchedule->struRecordSched[m_nDate][7].byRecordType = (BYTE)m_comboTimeRecType8.GetItemData(m_comboTimeRecType8.GetCurSel());
            
            m_struRemoteRecSchedule->struRecordSched[m_nDate][0].struRecordTime.byStartHour = (BYTE)m_iHour11;
            m_struRemoteRecSchedule->struRecordSched[m_nDate][0].struRecordTime.byStopHour = (BYTE)m_iHour12;
            m_struRemoteRecSchedule->struRecordSched[m_nDate][1].struRecordTime.byStartHour = (BYTE)m_iHour21;
            m_struRemoteRecSchedule->struRecordSched[m_nDate][1].struRecordTime.byStopHour = (BYTE)m_iHour22;
            m_struRemoteRecSchedule->struRecordSched[m_nDate][2].struRecordTime.byStartHour = (BYTE)m_iHour31;
            m_struRemoteRecSchedule->struRecordSched[m_nDate][2].struRecordTime.byStopHour = (BYTE)m_iHour32;
            m_struRemoteRecSchedule->struRecordSched[m_nDate][3].struRecordTime.byStartHour = (BYTE)m_iHour41;
            m_struRemoteRecSchedule->struRecordSched[m_nDate][3].struRecordTime.byStopHour = (BYTE)m_iHour42;
            
            m_struRemoteRecSchedule->struRecordSched[m_nDate][0].struRecordTime.byStartMin = (BYTE)m_iMin11;
            m_struRemoteRecSchedule->struRecordSched[m_nDate][0].struRecordTime.byStopMin = (BYTE)m_iMin12;
            m_struRemoteRecSchedule->struRecordSched[m_nDate][1].struRecordTime.byStartMin = (BYTE)m_iMin21;
            m_struRemoteRecSchedule->struRecordSched[m_nDate][1].struRecordTime.byStopMin = (BYTE)m_iMin22;
            m_struRemoteRecSchedule->struRecordSched[m_nDate][2].struRecordTime.byStartMin = (BYTE)m_iMin31;
            m_struRemoteRecSchedule->struRecordSched[m_nDate][2].struRecordTime.byStopMin = (BYTE)m_iMin32;
            m_struRemoteRecSchedule->struRecordSched[m_nDate][3].struRecordTime.byStartMin = (BYTE)m_iMin41;
            m_struRemoteRecSchedule->struRecordSched[m_nDate][3].struRecordTime.byStopMin = (BYTE)m_iMin42;
            
            m_struRemoteRecSchedule->struRecordSched[m_nDate][4].struRecordTime.byStartHour = (BYTE)m_iHour51;
            m_struRemoteRecSchedule->struRecordSched[m_nDate][4].struRecordTime.byStopHour = (BYTE)m_iHour52;
            m_struRemoteRecSchedule->struRecordSched[m_nDate][5].struRecordTime.byStartHour = (BYTE)m_iHour61;
            m_struRemoteRecSchedule->struRecordSched[m_nDate][5].struRecordTime.byStopHour = (BYTE)m_iHour62;
            m_struRemoteRecSchedule->struRecordSched[m_nDate][6].struRecordTime.byStartHour = (BYTE)m_iHour71;
            m_struRemoteRecSchedule->struRecordSched[m_nDate][6].struRecordTime.byStopHour = (BYTE)m_iHour72;
            m_struRemoteRecSchedule->struRecordSched[m_nDate][7].struRecordTime.byStartHour = (BYTE)m_iHour81;
            m_struRemoteRecSchedule->struRecordSched[m_nDate][7].struRecordTime.byStopHour = (BYTE)m_iHour82;
            
            m_struRemoteRecSchedule->struRecordSched[m_nDate][4].struRecordTime.byStartMin = (BYTE)m_iMin51;
            m_struRemoteRecSchedule->struRecordSched[m_nDate][4].struRecordTime.byStopMin = (BYTE)m_iMin52;
            m_struRemoteRecSchedule->struRecordSched[m_nDate][5].struRecordTime.byStartMin = (BYTE)m_iMin61;
            m_struRemoteRecSchedule->struRecordSched[m_nDate][5].struRecordTime.byStopMin = (BYTE)m_iMin62;
            m_struRemoteRecSchedule->struRecordSched[m_nDate][6].struRecordTime.byStartMin = (BYTE)m_iMin71;
            m_struRemoteRecSchedule->struRecordSched[m_nDate][6].struRecordTime.byStopMin = (BYTE)m_iMin72;
            m_struRemoteRecSchedule->struRecordSched[m_nDate][7].struRecordTime.byStartMin = (BYTE)m_iMin81;
            m_struRemoteRecSchedule->struRecordSched[m_nDate][7].struRecordTime.byStopMin = (BYTE)m_iMin82;
        }
        GetDlgItem(IDC_BTN_REMOTE_REC_COPY)->EnableWindow(TRUE);
    }

}

/*********************************************************
  Function:	OnBnClickedBtnRemoteRecExit
  Desc:		cancle record schedule settings
  Input:	
  Output:	
  Return:	
**********************************************************/
void CDlgRemoteRecordSchedule::OnBnClickedBtnRemoteRecExit()
{
	CDialog::OnOK();
}

/*********************************************************
Function:	OnBnClickedBtnRemoteRecCopy
Desc:		check and update the schedule settings
Input:	
Output:	
Return:	
**********************************************************/
void CDlgRemoteRecordSchedule::OnBnClickedBtnRemoteRecCopy()
{
	UpdateData(TRUE);
	m_nCopyDate = m_comboCopyWeekday.GetCurSel() - 1;
	if (!TimeTest())
	{
		return;
	}

	if (m_nCopyDate != -1)
	{
        if (m_nCopyDate == 7) // 假日
        {
            m_struHolidayRecord.struRecDay.wAllDayRecord = (WORD)m_bCheckAllDay;
            m_struHolidayRecord.struRecDay.byRecordType = (BYTE)m_comboAllDayType.GetItemData(m_comboAllDayType.GetCurSel());		
            m_struHolidayRecord.struRecordSched[0].byRecordType = (BYTE)m_comboTimeRecType1.GetItemData(m_comboTimeRecType1.GetCurSel());
            m_struHolidayRecord.struRecordSched[1].byRecordType = (BYTE)m_comboTimeRecType2.GetItemData(m_comboTimeRecType2.GetCurSel());
            m_struHolidayRecord.struRecordSched[2].byRecordType = (BYTE)m_comboTimeRecType3.GetItemData(m_comboTimeRecType3.GetCurSel());
            m_struHolidayRecord.struRecordSched[3].byRecordType = (BYTE)m_comboTimeRecType4.GetItemData(m_comboTimeRecType4.GetCurSel());
			m_struHolidayRecord.struRecordSched[4].byRecordType = (BYTE)m_comboTimeRecType5.GetItemData(m_comboTimeRecType5.GetCurSel());
            m_struHolidayRecord.struRecordSched[5].byRecordType = (BYTE)m_comboTimeRecType6.GetItemData(m_comboTimeRecType6.GetCurSel());
            m_struHolidayRecord.struRecordSched[6].byRecordType = (BYTE)m_comboTimeRecType7.GetItemData(m_comboTimeRecType7.GetCurSel());
            m_struHolidayRecord.struRecordSched[7].byRecordType = (BYTE)m_comboTimeRecType8.GetItemData(m_comboTimeRecType8.GetCurSel());

            m_struHolidayRecord.struRecordSched[0].struRecordTime.byStartHour = (BYTE)m_iHour11;
            m_struHolidayRecord.struRecordSched[0].struRecordTime.byStopHour = (BYTE)m_iHour12;
            m_struHolidayRecord.struRecordSched[1].struRecordTime.byStartHour = (BYTE)m_iHour21;
            m_struHolidayRecord.struRecordSched[1].struRecordTime.byStopHour = (BYTE)m_iHour22;
            m_struHolidayRecord.struRecordSched[2].struRecordTime.byStartHour = (BYTE)m_iHour31;
            m_struHolidayRecord.struRecordSched[2].struRecordTime.byStopHour = (BYTE)m_iHour32;
            m_struHolidayRecord.struRecordSched[3].struRecordTime.byStartHour = (BYTE)m_iHour41;
            m_struHolidayRecord.struRecordSched[3].struRecordTime.byStopHour = (BYTE)m_iHour42;
			m_struHolidayRecord.struRecordSched[4].struRecordTime.byStartHour = (BYTE)m_iHour51;
            m_struHolidayRecord.struRecordSched[4].struRecordTime.byStopHour = (BYTE)m_iHour52;
            m_struHolidayRecord.struRecordSched[5].struRecordTime.byStartHour = (BYTE)m_iHour61;
            m_struHolidayRecord.struRecordSched[5].struRecordTime.byStopHour = (BYTE)m_iHour62;
            m_struHolidayRecord.struRecordSched[6].struRecordTime.byStartHour = (BYTE)m_iHour71;
            m_struHolidayRecord.struRecordSched[6].struRecordTime.byStopHour = (BYTE)m_iHour72;
            m_struHolidayRecord.struRecordSched[7].struRecordTime.byStartHour = (BYTE)m_iHour81;
            m_struHolidayRecord.struRecordSched[7].struRecordTime.byStopHour = (BYTE)m_iHour82;
            
            m_struHolidayRecord.struRecordSched[0].struRecordTime.byStartMin = (BYTE)m_iMin11;
            m_struHolidayRecord.struRecordSched[0].struRecordTime.byStopMin = (BYTE)m_iMin12;
            m_struHolidayRecord.struRecordSched[1].struRecordTime.byStartMin = (BYTE)m_iMin21;
            m_struHolidayRecord.struRecordSched[1].struRecordTime.byStopMin = (BYTE)m_iMin22;
            m_struHolidayRecord.struRecordSched[2].struRecordTime.byStartMin = (BYTE)m_iMin31;
            m_struHolidayRecord.struRecordSched[2].struRecordTime.byStopMin = (BYTE)m_iMin32;
            m_struHolidayRecord.struRecordSched[3].struRecordTime.byStartMin = (BYTE)m_iMin41;
            m_struHolidayRecord.struRecordSched[3].struRecordTime.byStopMin = (BYTE)m_iMin42;
			m_struHolidayRecord.struRecordSched[4].struRecordTime.byStartMin = (BYTE)m_iMin51;
            m_struHolidayRecord.struRecordSched[4].struRecordTime.byStopMin = (BYTE)m_iMin52;
            m_struHolidayRecord.struRecordSched[5].struRecordTime.byStartMin = (BYTE)m_iMin61;
            m_struHolidayRecord.struRecordSched[5].struRecordTime.byStopMin = (BYTE)m_iMin62;
            m_struHolidayRecord.struRecordSched[6].struRecordTime.byStartMin = (BYTE)m_iMin71;
            m_struHolidayRecord.struRecordSched[6].struRecordTime.byStopMin = (BYTE)m_iMin72;
            m_struHolidayRecord.struRecordSched[7].struRecordTime.byStartMin = (BYTE)m_iMin81;
            m_struHolidayRecord.struRecordSched[7].struRecordTime.byStopMin = (BYTE)m_iMin82;
            if (!SetHolidayRecord(m_struHolidayRecord))
            {
                AfxMessageBox("Fail to set holiday record");
            }
        }
        else
        {
            m_struRemoteRecSchedule->struRecAllDay[m_nCopyDate].wAllDayRecord = (WORD)m_bCheckAllDay;
            m_struRemoteRecSchedule->struRecAllDay[m_nCopyDate].byRecordType = (BYTE)m_comboAllDayType.GetItemData(m_comboAllDayType.GetCurSel());		
            m_struRemoteRecSchedule->struRecordSched[m_nCopyDate][0].byRecordType = (BYTE)m_comboTimeRecType1.GetItemData(m_comboTimeRecType1.GetCurSel());
            m_struRemoteRecSchedule->struRecordSched[m_nCopyDate][1].byRecordType = (BYTE)m_comboTimeRecType2.GetItemData(m_comboTimeRecType2.GetCurSel());
            m_struRemoteRecSchedule->struRecordSched[m_nCopyDate][2].byRecordType = (BYTE)m_comboTimeRecType3.GetItemData(m_comboTimeRecType3.GetCurSel());
            m_struRemoteRecSchedule->struRecordSched[m_nCopyDate][3].byRecordType = (BYTE)m_comboTimeRecType4.GetItemData(m_comboTimeRecType4.GetCurSel());
			m_struRemoteRecSchedule->struRecordSched[m_nCopyDate][3].byRecordType = (BYTE)m_comboTimeRecType4.GetItemData(m_comboTimeRecType4.GetCurSel());	
			m_struRemoteRecSchedule->struRecordSched[m_nCopyDate][4].byRecordType = (BYTE)m_comboTimeRecType5.GetItemData(m_comboTimeRecType5.GetCurSel());
			m_struRemoteRecSchedule->struRecordSched[m_nCopyDate][5].byRecordType = (BYTE)m_comboTimeRecType6.GetItemData(m_comboTimeRecType6.GetCurSel());
			m_struRemoteRecSchedule->struRecordSched[m_nCopyDate][6].byRecordType = (BYTE)m_comboTimeRecType7.GetItemData(m_comboTimeRecType7.GetCurSel());
			m_struRemoteRecSchedule->struRecordSched[m_nCopyDate][7].byRecordType = (BYTE)m_comboTimeRecType8.GetItemData(m_comboTimeRecType8.GetCurSel());

            m_struRemoteRecSchedule->struRecordSched[m_nCopyDate][0].struRecordTime.byStartHour = (BYTE)m_iHour11;
            m_struRemoteRecSchedule->struRecordSched[m_nCopyDate][0].struRecordTime.byStopHour = (BYTE)m_iHour12;
            m_struRemoteRecSchedule->struRecordSched[m_nCopyDate][1].struRecordTime.byStartHour = (BYTE)m_iHour21;
            m_struRemoteRecSchedule->struRecordSched[m_nCopyDate][1].struRecordTime.byStopHour = (BYTE)m_iHour22;
            m_struRemoteRecSchedule->struRecordSched[m_nCopyDate][2].struRecordTime.byStartHour = (BYTE)m_iHour31;
            m_struRemoteRecSchedule->struRecordSched[m_nCopyDate][2].struRecordTime.byStopHour = (BYTE)m_iHour32;
            m_struRemoteRecSchedule->struRecordSched[m_nCopyDate][3].struRecordTime.byStartHour = (BYTE)m_iHour41;
            m_struRemoteRecSchedule->struRecordSched[m_nCopyDate][3].struRecordTime.byStopHour = (BYTE)m_iHour42;
			m_struRemoteRecSchedule->struRecordSched[m_nCopyDate][4].struRecordTime.byStartHour = (BYTE)m_iHour51;
			m_struRemoteRecSchedule->struRecordSched[m_nCopyDate][4].struRecordTime.byStopHour = (BYTE)m_iHour52;
			m_struRemoteRecSchedule->struRecordSched[m_nCopyDate][5].struRecordTime.byStartHour = (BYTE)m_iHour61;
			m_struRemoteRecSchedule->struRecordSched[m_nCopyDate][5].struRecordTime.byStopHour = (BYTE)m_iHour62;
			m_struRemoteRecSchedule->struRecordSched[m_nCopyDate][6].struRecordTime.byStartHour = (BYTE)m_iHour71;
			m_struRemoteRecSchedule->struRecordSched[m_nCopyDate][6].struRecordTime.byStopHour = (BYTE)m_iHour72;
			m_struRemoteRecSchedule->struRecordSched[m_nCopyDate][7].struRecordTime.byStartHour = (BYTE)m_iHour81;
			m_struRemoteRecSchedule->struRecordSched[m_nCopyDate][7].struRecordTime.byStopHour = (BYTE)m_iHour82;
            
            m_struRemoteRecSchedule->struRecordSched[m_nCopyDate][0].struRecordTime.byStartMin = (BYTE)m_iMin11;
            m_struRemoteRecSchedule->struRecordSched[m_nCopyDate][0].struRecordTime.byStopMin = (BYTE)m_iMin12;
            m_struRemoteRecSchedule->struRecordSched[m_nCopyDate][1].struRecordTime.byStartMin = (BYTE)m_iMin21;
            m_struRemoteRecSchedule->struRecordSched[m_nCopyDate][1].struRecordTime.byStopMin = (BYTE)m_iMin22;
            m_struRemoteRecSchedule->struRecordSched[m_nCopyDate][2].struRecordTime.byStartMin = (BYTE)m_iMin31;
            m_struRemoteRecSchedule->struRecordSched[m_nCopyDate][2].struRecordTime.byStopMin = (BYTE)m_iMin32;
            m_struRemoteRecSchedule->struRecordSched[m_nCopyDate][3].struRecordTime.byStartMin = (BYTE)m_iMin41;
            m_struRemoteRecSchedule->struRecordSched[m_nCopyDate][3].struRecordTime.byStopMin = (BYTE)m_iMin42;
			m_struRemoteRecSchedule->struRecordSched[m_nCopyDate][4].struRecordTime.byStartMin = (BYTE)m_iMin51;
			m_struRemoteRecSchedule->struRecordSched[m_nCopyDate][4].struRecordTime.byStopMin = (BYTE)m_iMin52;
			m_struRemoteRecSchedule->struRecordSched[m_nCopyDate][5].struRecordTime.byStartMin = (BYTE)m_iMin61;
			m_struRemoteRecSchedule->struRecordSched[m_nCopyDate][5].struRecordTime.byStopMin = (BYTE)m_iMin62;
			m_struRemoteRecSchedule->struRecordSched[m_nCopyDate][6].struRecordTime.byStartMin = (BYTE)m_iMin71;
			m_struRemoteRecSchedule->struRecordSched[m_nCopyDate][6].struRecordTime.byStopMin = (BYTE)m_iMin72;
			m_struRemoteRecSchedule->struRecordSched[m_nCopyDate][7].struRecordTime.byStartMin = (BYTE)m_iMin81;
			m_struRemoteRecSchedule->struRecordSched[m_nCopyDate][7].struRecordTime.byStopMin = (BYTE)m_iMin82;
        }
	}
	else
	{
		for (int i = 0;i < MAX_DAYS;i++)
		{	
			m_struRemoteRecSchedule->struRecAllDay[i].wAllDayRecord = (WORD)m_bCheckAllDay;
			m_struRemoteRecSchedule->struRecAllDay[i].byRecordType = (BYTE)m_comboAllDayType.GetItemData(m_comboAllDayType.GetCurSel());	

			m_struRemoteRecSchedule->struRecordSched[i][0].byRecordType = (BYTE)m_comboTimeRecType1.GetItemData(m_comboTimeRecType1.GetCurSel());
			m_struRemoteRecSchedule->struRecordSched[i][1].byRecordType = (BYTE)m_comboTimeRecType2.GetItemData(m_comboTimeRecType2.GetCurSel());
			m_struRemoteRecSchedule->struRecordSched[i][2].byRecordType = (BYTE)m_comboTimeRecType3.GetItemData(m_comboTimeRecType3.GetCurSel());
			m_struRemoteRecSchedule->struRecordSched[i][3].byRecordType = (BYTE)m_comboTimeRecType4.GetItemData(m_comboTimeRecType4.GetCurSel());	
			m_struRemoteRecSchedule->struRecordSched[i][4].byRecordType = (BYTE)m_comboTimeRecType5.GetItemData(m_comboTimeRecType5.GetCurSel());
			m_struRemoteRecSchedule->struRecordSched[i][5].byRecordType = (BYTE)m_comboTimeRecType6.GetItemData(m_comboTimeRecType6.GetCurSel());
			m_struRemoteRecSchedule->struRecordSched[i][6].byRecordType = (BYTE)m_comboTimeRecType7.GetItemData(m_comboTimeRecType7.GetCurSel());
			m_struRemoteRecSchedule->struRecordSched[i][7].byRecordType = (BYTE)m_comboTimeRecType8.GetItemData(m_comboTimeRecType8.GetCurSel());	

			m_struRemoteRecSchedule->struRecordSched[i][0].struRecordTime.byStartHour = (BYTE)m_iHour11;
			m_struRemoteRecSchedule->struRecordSched[i][0].struRecordTime.byStopHour = (BYTE)m_iHour12;
			m_struRemoteRecSchedule->struRecordSched[i][1].struRecordTime.byStartHour = (BYTE)m_iHour21;
			m_struRemoteRecSchedule->struRecordSched[i][1].struRecordTime.byStopHour = (BYTE)m_iHour22;
			m_struRemoteRecSchedule->struRecordSched[i][2].struRecordTime.byStartHour = (BYTE)m_iHour31;
			m_struRemoteRecSchedule->struRecordSched[i][2].struRecordTime.byStopHour = (BYTE)m_iHour32;
			m_struRemoteRecSchedule->struRecordSched[i][3].struRecordTime.byStartHour = (BYTE)m_iHour41;
			m_struRemoteRecSchedule->struRecordSched[i][3].struRecordTime.byStopHour = (BYTE)m_iHour42;
			m_struRemoteRecSchedule->struRecordSched[i][4].struRecordTime.byStartHour = (BYTE)m_iHour51;
			m_struRemoteRecSchedule->struRecordSched[i][4].struRecordTime.byStopHour = (BYTE)m_iHour52;
			m_struRemoteRecSchedule->struRecordSched[i][5].struRecordTime.byStartHour = (BYTE)m_iHour61;
			m_struRemoteRecSchedule->struRecordSched[i][5].struRecordTime.byStopHour = (BYTE)m_iHour62;
			m_struRemoteRecSchedule->struRecordSched[i][6].struRecordTime.byStartHour = (BYTE)m_iHour71;
			m_struRemoteRecSchedule->struRecordSched[i][6].struRecordTime.byStopHour = (BYTE)m_iHour72;
			m_struRemoteRecSchedule->struRecordSched[i][7].struRecordTime.byStartHour = (BYTE)m_iHour81;
			m_struRemoteRecSchedule->struRecordSched[i][7].struRecordTime.byStopHour = (BYTE)m_iHour82;

			m_struRemoteRecSchedule->struRecordSched[i][0].struRecordTime.byStartMin = (BYTE)m_iMin11;
			m_struRemoteRecSchedule->struRecordSched[i][0].struRecordTime.byStopMin = (BYTE)m_iMin12;
			m_struRemoteRecSchedule->struRecordSched[i][1].struRecordTime.byStartMin = (BYTE)m_iMin21;
			m_struRemoteRecSchedule->struRecordSched[i][1].struRecordTime.byStopMin = (BYTE)m_iMin22;
			m_struRemoteRecSchedule->struRecordSched[i][2].struRecordTime.byStartMin = (BYTE)m_iMin31;
			m_struRemoteRecSchedule->struRecordSched[i][2].struRecordTime.byStopMin = (BYTE)m_iMin32;
			m_struRemoteRecSchedule->struRecordSched[i][3].struRecordTime.byStartMin = (BYTE)m_iMin41;
			m_struRemoteRecSchedule->struRecordSched[i][3].struRecordTime.byStopMin = (BYTE)m_iMin42;
			m_struRemoteRecSchedule->struRecordSched[i][4].struRecordTime.byStartMin = (BYTE)m_iMin51;
			m_struRemoteRecSchedule->struRecordSched[i][4].struRecordTime.byStopMin = (BYTE)m_iMin52;
			m_struRemoteRecSchedule->struRecordSched[i][5].struRecordTime.byStartMin = (BYTE)m_iMin61;
			m_struRemoteRecSchedule->struRecordSched[i][5].struRecordTime.byStopMin = (BYTE)m_iMin62;
			m_struRemoteRecSchedule->struRecordSched[i][6].struRecordTime.byStartMin = (BYTE)m_iMin71;
			m_struRemoteRecSchedule->struRecordSched[i][6].struRecordTime.byStopMin = (BYTE)m_iMin72;
			m_struRemoteRecSchedule->struRecordSched[i][7].struRecordTime.byStartMin = (BYTE)m_iMin81;
			m_struRemoteRecSchedule->struRecordSched[i][7].struRecordTime.byStopMin = (BYTE)m_iMin82;
		}
	}
}

/*********************************************************
  Function:	OnCbnSelchangeComboWeekDay
  Desc:		display schedule for selected date
  Input:	
  Output:	
  Return:	
**********************************************************/
void CDlgRemoteRecordSchedule::OnCbnSelchangeComboWeekDay()
{
	int i;
	m_nDate = m_comboWeekday.GetCurSel();	
	if (m_nDate == 7) // 假日录像计划 
	{
        GetHolidayRecord(m_struHolidayRecord);
        
        m_bCheckAllDay = m_struHolidayRecord.struRecDay.wAllDayRecord;
		for (i=0; i<m_comboAllDayType.GetCount(); i++)
		{
			if (m_struHolidayRecord.struRecDay.byRecordType == m_comboAllDayType.GetItemData(i))
			{
				m_comboAllDayType.SetCurSel(i);
			}
		}
		for (i=0; i<m_comboTimeRecType1.GetCount(); i++)
		{
			if (m_struHolidayRecord.struRecordSched[0].byRecordType == m_comboTimeRecType1.GetItemData(i))
			{
				m_comboTimeRecType1.SetCurSel(i);
			}
		}
		for (i=0; i<m_comboTimeRecType2.GetCount(); i++)
		{
			if (m_struHolidayRecord.struRecordSched[1].byRecordType == m_comboTimeRecType2.GetItemData(i))
			{
				m_comboTimeRecType2.SetCurSel(i);
			}
		}
		for (i=0; i<m_comboTimeRecType3.GetCount(); i++)
		{
			if (m_struHolidayRecord.struRecordSched[2].byRecordType == m_comboTimeRecType3.GetItemData(i))
			{
				m_comboTimeRecType3.SetCurSel(i);
			}
		}
		for (i=0; i<m_comboTimeRecType4.GetCount(); i++)
		{
			if (m_struHolidayRecord.struRecordSched[3].byRecordType == m_comboTimeRecType4.GetItemData(i))
			{
				m_comboTimeRecType4.SetCurSel(i);
			}
		}
		for (i=0; i<m_comboTimeRecType5.GetCount(); i++)
		{
			if (m_struHolidayRecord.struRecordSched[4].byRecordType == m_comboTimeRecType5.GetItemData(i))
			{
				m_comboTimeRecType5.SetCurSel(i);
			}
		}
		for (i=0; i<m_comboTimeRecType6.GetCount(); i++)
		{
			if (m_struHolidayRecord.struRecordSched[5].byRecordType == m_comboTimeRecType6.GetItemData(i))
			{
				m_comboTimeRecType6.SetCurSel(i);
			}
		}
		for (i=0; i<m_comboTimeRecType7.GetCount(); i++)
		{
			if (m_struHolidayRecord.struRecordSched[6].byRecordType == m_comboTimeRecType7.GetItemData(i))
			{
				m_comboTimeRecType7.SetCurSel(i);
			}
		}
		for (i=0; i<m_comboTimeRecType8.GetCount(); i++)
		{
			if (m_struHolidayRecord.struRecordSched[7].byRecordType == m_comboTimeRecType8.GetItemData(i))
			{
				m_comboTimeRecType8.SetCurSel(i);
			}
		}

//         m_comboAllDayType.SetCurSel(m_struHolidayRecord.struRecDay.byRecordType);
//         m_comboTimeRecType1.SetCurSel(m_struHolidayRecord.struRecordSched[0].byRecordType);
//         m_comboTimeRecType2.SetCurSel(m_struHolidayRecord.struRecordSched[1].byRecordType);
//         m_comboTimeRecType3.SetCurSel(m_struHolidayRecord.struRecordSched[2].byRecordType);
//         m_comboTimeRecType4.SetCurSel(m_struHolidayRecord.struRecordSched[3].byRecordType);
        m_iHour11 = m_struHolidayRecord.struRecordSched[0].struRecordTime.byStartHour;
        m_iHour12 = m_struHolidayRecord.struRecordSched[0].struRecordTime.byStopHour;
        m_iHour21 = m_struHolidayRecord.struRecordSched[1].struRecordTime.byStartHour;
        m_iHour22 = m_struHolidayRecord.struRecordSched[1].struRecordTime.byStopHour;
        m_iHour31 = m_struHolidayRecord.struRecordSched[2].struRecordTime.byStartHour;
        m_iHour32 = m_struHolidayRecord.struRecordSched[2].struRecordTime.byStopHour;
        m_iHour41 = m_struHolidayRecord.struRecordSched[3].struRecordTime.byStartHour;
        m_iHour42 = m_struHolidayRecord.struRecordSched[3].struRecordTime.byStopHour;
		m_iHour51 = m_struHolidayRecord.struRecordSched[4].struRecordTime.byStartHour;
        m_iHour52 = m_struHolidayRecord.struRecordSched[4].struRecordTime.byStopHour;
        m_iHour61 = m_struHolidayRecord.struRecordSched[5].struRecordTime.byStartHour;
        m_iHour62 = m_struHolidayRecord.struRecordSched[5].struRecordTime.byStopHour;
        m_iHour71 = m_struHolidayRecord.struRecordSched[6].struRecordTime.byStartHour;
        m_iHour72 = m_struHolidayRecord.struRecordSched[6].struRecordTime.byStopHour;
        m_iHour81 = m_struHolidayRecord.struRecordSched[7].struRecordTime.byStartHour;
        m_iHour82 = m_struHolidayRecord.struRecordSched[7].struRecordTime.byStopHour;
        m_iMin11 = m_struHolidayRecord.struRecordSched[0].struRecordTime.byStartMin;
        m_iMin12 = m_struHolidayRecord.struRecordSched[0].struRecordTime.byStopMin;
        m_iMin21 = m_struHolidayRecord.struRecordSched[1].struRecordTime.byStartMin;
        m_iMin22 = m_struHolidayRecord.struRecordSched[1].struRecordTime.byStopMin;
        m_iMin31 = m_struHolidayRecord.struRecordSched[2].struRecordTime.byStartMin;
        m_iMin32 = m_struHolidayRecord.struRecordSched[2].struRecordTime.byStopMin;
        m_iMin41 = m_struHolidayRecord.struRecordSched[3].struRecordTime.byStartMin;
        m_iMin42 = m_struHolidayRecord.struRecordSched[3].struRecordTime.byStopMin;
		m_iMin51 = m_struHolidayRecord.struRecordSched[4].struRecordTime.byStartMin;
        m_iMin52 = m_struHolidayRecord.struRecordSched[4].struRecordTime.byStopMin;
        m_iMin61 = m_struHolidayRecord.struRecordSched[5].struRecordTime.byStartMin;
        m_iMin62 = m_struHolidayRecord.struRecordSched[5].struRecordTime.byStopMin;
        m_iMin71 = m_struHolidayRecord.struRecordSched[6].struRecordTime.byStartMin;
        m_iMin72 = m_struHolidayRecord.struRecordSched[6].struRecordTime.byStopMin;
        m_iMin81 = m_struHolidayRecord.struRecordSched[7].struRecordTime.byStartMin;
        m_iMin82 = m_struHolidayRecord.struRecordSched[7].struRecordTime.byStopMin;

	}
    else
    {
        m_bCheckAllDay = m_struRemoteRecSchedule->struRecAllDay[m_nDate].wAllDayRecord;
		for (i=0; i<m_comboAllDayType.GetCount(); i++)
		{
			if (m_struRemoteRecSchedule->struRecAllDay[m_nDate].byRecordType == m_comboAllDayType.GetItemData(i))
			{
				m_comboAllDayType.SetCurSel(i);
			}
		}
		for (i=0; i<m_comboTimeRecType1.GetCount(); i++)
		{
			if (m_struRemoteRecSchedule->struRecordSched[m_nDate][0].byRecordType == m_comboTimeRecType1.GetItemData(i))
			{
				m_comboTimeRecType1.SetCurSel(i);
			}
		}
		for (i=0; i<m_comboTimeRecType2.GetCount(); i++)
		{
			if (m_struRemoteRecSchedule->struRecordSched[m_nDate][1].byRecordType == m_comboTimeRecType2.GetItemData(i))
			{
				m_comboTimeRecType2.SetCurSel(i);
			}
		}
		for (i=0; i<m_comboTimeRecType3.GetCount(); i++)
		{
			if (m_struRemoteRecSchedule->struRecordSched[m_nDate][2].byRecordType == m_comboTimeRecType3.GetItemData(i))
			{
				m_comboTimeRecType3.SetCurSel(i);
			}
		}
		for (i=0; i<m_comboTimeRecType4.GetCount(); i++)
		{
			if (m_struRemoteRecSchedule->struRecordSched[m_nDate][3].byRecordType == m_comboTimeRecType4.GetItemData(i))
			{
				m_comboTimeRecType4.SetCurSel(i);
			}
		}
		for (i=0; i<m_comboTimeRecType5.GetCount(); i++)
		{
			if (m_struRemoteRecSchedule->struRecordSched[m_nDate][4].byRecordType == m_comboTimeRecType5.GetItemData(i))
			{
				m_comboTimeRecType5.SetCurSel(i);
			}
		}
		for (i=0; i<m_comboTimeRecType6.GetCount(); i++)
		{
			if (m_struRemoteRecSchedule->struRecordSched[m_nDate][5].byRecordType == m_comboTimeRecType6.GetItemData(i))
			{
				m_comboTimeRecType6.SetCurSel(i);
			}
		}
		for (i=0; i<m_comboTimeRecType7.GetCount(); i++)
		{
			if (m_struRemoteRecSchedule->struRecordSched[m_nDate][6].byRecordType == m_comboTimeRecType7.GetItemData(i))
			{
				m_comboTimeRecType7.SetCurSel(i);
			}
		}
		for (i=0; i<m_comboTimeRecType8.GetCount(); i++)
		{
			if (m_struRemoteRecSchedule->struRecordSched[m_nDate][7].byRecordType == m_comboTimeRecType8.GetItemData(i))
			{
				m_comboTimeRecType8.SetCurSel(i);
			}
		}
//         m_comboAllDayType.SetCurSel(m_struRemoteRecSchedule->struRecAllDay[m_nDate].byRecordType);
//         m_comboTimeRecType1.SetCurSel(m_struRemoteRecSchedule->struRecordSched[m_nDate][0].byRecordType);
//         m_comboTimeRecType2.SetCurSel(m_struRemoteRecSchedule->struRecordSched[m_nDate][1].byRecordType);
//         m_comboTimeRecType3.SetCurSel(m_struRemoteRecSchedule->struRecordSched[m_nDate][2].byRecordType);
//         m_comboTimeRecType4.SetCurSel(m_struRemoteRecSchedule->struRecordSched[m_nDate][3].byRecordType);
        m_iHour11 = m_struRemoteRecSchedule->struRecordSched[m_nDate][0].struRecordTime.byStartHour;
		m_iHour12 = m_struRemoteRecSchedule->struRecordSched[m_nDate][0].struRecordTime.byStopHour;
		m_iHour21 = m_struRemoteRecSchedule->struRecordSched[m_nDate][1].struRecordTime.byStartHour;
		m_iHour22 = m_struRemoteRecSchedule->struRecordSched[m_nDate][1].struRecordTime.byStopHour;
		m_iHour31 = m_struRemoteRecSchedule->struRecordSched[m_nDate][2].struRecordTime.byStartHour;
		m_iHour32 = m_struRemoteRecSchedule->struRecordSched[m_nDate][2].struRecordTime.byStopHour;
		m_iHour41 = m_struRemoteRecSchedule->struRecordSched[m_nDate][3].struRecordTime.byStartHour;
		m_iHour42 = m_struRemoteRecSchedule->struRecordSched[m_nDate][3].struRecordTime.byStopHour;
		m_iHour51 = m_struRemoteRecSchedule->struRecordSched[m_nDate][4].struRecordTime.byStartHour;
		m_iHour52 = m_struRemoteRecSchedule->struRecordSched[m_nDate][4].struRecordTime.byStopHour;
		m_iHour61 = m_struRemoteRecSchedule->struRecordSched[m_nDate][5].struRecordTime.byStartHour;
		m_iHour62 = m_struRemoteRecSchedule->struRecordSched[m_nDate][5].struRecordTime.byStopHour;
		m_iHour71 = m_struRemoteRecSchedule->struRecordSched[m_nDate][6].struRecordTime.byStartHour;
		m_iHour72 = m_struRemoteRecSchedule->struRecordSched[m_nDate][6].struRecordTime.byStopHour;
		m_iHour81 = m_struRemoteRecSchedule->struRecordSched[m_nDate][7].struRecordTime.byStartHour;
		m_iHour82 = m_struRemoteRecSchedule->struRecordSched[m_nDate][7].struRecordTime.byStopHour;
		m_iMin11 = m_struRemoteRecSchedule->struRecordSched[m_nDate][0].struRecordTime.byStartMin;
		m_iMin12 = m_struRemoteRecSchedule->struRecordSched[m_nDate][0].struRecordTime.byStopMin;
		m_iMin21 = m_struRemoteRecSchedule->struRecordSched[m_nDate][1].struRecordTime.byStartMin;
		m_iMin22 = m_struRemoteRecSchedule->struRecordSched[m_nDate][1].struRecordTime.byStopMin;
		m_iMin31 = m_struRemoteRecSchedule->struRecordSched[m_nDate][2].struRecordTime.byStartMin;
		m_iMin32 = m_struRemoteRecSchedule->struRecordSched[m_nDate][2].struRecordTime.byStopMin;
		m_iMin41 = m_struRemoteRecSchedule->struRecordSched[m_nDate][3].struRecordTime.byStartMin;
		m_iMin42 = m_struRemoteRecSchedule->struRecordSched[m_nDate][3].struRecordTime.byStopMin;
		m_iMin51 = m_struRemoteRecSchedule->struRecordSched[m_nDate][4].struRecordTime.byStartMin;
		m_iMin52 = m_struRemoteRecSchedule->struRecordSched[m_nDate][4].struRecordTime.byStopMin;
		m_iMin61 = m_struRemoteRecSchedule->struRecordSched[m_nDate][5].struRecordTime.byStartMin;
		m_iMin62 = m_struRemoteRecSchedule->struRecordSched[m_nDate][5].struRecordTime.byStopMin;
		m_iMin71 = m_struRemoteRecSchedule->struRecordSched[m_nDate][6].struRecordTime.byStartMin;
		m_iMin72 = m_struRemoteRecSchedule->struRecordSched[m_nDate][6].struRecordTime.byStopMin;
		m_iMin81 = m_struRemoteRecSchedule->struRecordSched[m_nDate][7].struRecordTime.byStartMin;
		m_iMin82 = m_struRemoteRecSchedule->struRecordSched[m_nDate][7].struRecordTime.byStopMin;
    }
	EnableControl(!m_bCheckAllDay);
	GetDlgItem(IDC_BTN_REMOTE_REC_COPY)->EnableWindow(FALSE);
	UpdateData(FALSE);
}

/*********************************************************
  Function:	OnBnClickedChkAllDay
  Desc:		all day recording
  Input:	
  Output:	
  Return:	
**********************************************************/
void CDlgRemoteRecordSchedule::OnBnClickedChkAllDay()
{
	UpdateData(TRUE);
	EnableControl(!m_bCheckAllDay);
}

BOOL CDlgRemoteRecordSchedule::GetHolidayRecord(NET_DVR_HOLIDAY_RECORD &struHolidayRecord)
{
    DWORD dwReturn = 0;
    if (NET_DVR_GetDVRConfig(m_lServerID, NET_DVR_GET_HOLIDAY_RECORD, m_lChannel, &struHolidayRecord, sizeof(struHolidayRecord), &dwReturn))
    {
        g_pMainDlg->AddLog(m_iDevIndex, OPERATION_SUCC_T, "NET_DVR_GET_HOLIDAY_RECORD");
        return TRUE;
    } 
    else
    {
        g_pMainDlg->AddLog(m_iDevIndex, OPERATION_FAIL_T, "NET_DVR_GET_HOLIDAY_RECORD");
        return FALSE;
    }
}

BOOL CDlgRemoteRecordSchedule::SetHolidayRecord(NET_DVR_HOLIDAY_RECORD &struHolidayRecord)
{
    if (NET_DVR_SetDVRConfig(m_lServerID, NET_DVR_SET_HOLIDAY_RECORD, m_lChannel, &struHolidayRecord, sizeof(struHolidayRecord)))
    {
        g_pMainDlg->AddLog(m_iDevIndex, OPERATION_SUCC_T, "NET_DVR_SET_HOLIDAY_RECORD");
        return TRUE;
    } 
    else
    {
        g_pMainDlg->AddLog(m_iDevIndex, OPERATION_FAIL_T, "NET_DVR_SET_HOLIDAY_RECORD");
        return FALSE;
    }
}
