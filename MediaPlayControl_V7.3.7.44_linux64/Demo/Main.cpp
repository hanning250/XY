#define _CRT_SECURE_NO_WARNINGS
#include <stdio.h>
#include <string>
#include <iostream>
#include <memory.h>
#include <time.h>
#include <thread>
#include <unistd.h> 

using namespace std;
#include "./PlayM4.h"
#include "./HCNetSDK.h"
#include "./iniFile.h"
#define STD_MAX_FILE_PATH_LENGTH	256
int times = 0;
LONG lRealPlayHandle;
LONG m_lPort[16] = { -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1 };//全局的播放库port号
//播放库硬解码回调
void CALLBACK DisplayCBFun(DISPLAY_INFO_YUV* pstDisplayInfo) {

	if (times % 100 == 0) {
		FILE* fp = NULL;
		string ansiString = "example" + to_string(pstDisplayInfo->nPort) + "___" + to_string(times / 100) + ".yuv";
		fp = fopen(ansiString.c_str(), "wb");
		// 将字符数组写入文件
		fwrite(pstDisplayInfo->pBuf, sizeof(char), pstDisplayInfo->nBufLen, fp); // 不包括末尾的空字符
		// 关闭文件
		fclose(fp);

	}
	times++;
	printf("Buf长度:%d\n画面宽:%d\n画面高:%d\n数据类型:%d\nn播放库句柄:%d\n", pstDisplayInfo->nBufLen, pstDisplayInfo->nWidth, pstDisplayInfo->nHeight, pstDisplayInfo->nType, pstDisplayInfo->nPort);
}
//播放库解码回调
void CALLBACK DecCBFunIm(int nPort, char* pBuf, int nSize, FRAME_INFO* pFrameInfo, void* nUser, int nReserved2) {
	printf("字节数据大小：%d\n", nSize);
	printf("相对时间戳：%d\n", pFrameInfo->nStamp);
	//将yuv数据转为jpg文件
	//每100次回调保存一次数据
	if (times % 100 == 0) {
		string ansiString = "example" + to_string(pFrameInfo->nStamp) + "___" + to_string(nPort / 100) + ".jpg";
		PlayM4_ConvertToJpegFile(pBuf, nSize, pFrameInfo->nWidth, pFrameInfo->nHeight, pFrameInfo->nType, &ansiString[0]);
		//将yuv数据转为bmp文件
		string ansiStrings = "example" + to_string(pFrameInfo->nStamp) + "___" + to_string(nPort / 100) + ".bmp";
		PlayM4_ConvertToBmpFile(pBuf, nSize, pFrameInfo->nWidth, pFrameInfo->nHeight, pFrameInfo->nType, &ansiStrings[0]);
	}
	times++;
}

//播放库抓图
void getPic() {
	int i = 0;
	BOOL   bFlag = FALSE;
	DWORD  dwErr = 0;
	LONG dwWidth = 0;
	LONG dwHeight = 0;
	DWORD dwSize = 0;
	DWORD dwCapSize = 0;

	//抓10张图
	while (i++ < 10) {

		//获取当前视频文件的分辨率
		int bFlag = PlayM4_GetPictureSize(m_lPort[lRealPlayHandle], &dwWidth, &dwHeight);
		if (bFlag == FALSE)
		{
			dwErr = PlayM4_GetLastError(m_lPort[lRealPlayHandle]);
			printf("PlayM4_GetPictureSize, error code: %d\n", dwErr);
			break;
		}
		dwSize = dwWidth * dwHeight * 5;
		//申请抓图内存
		BYTE* m_pCapBuf = NULL;
		if (m_pCapBuf == NULL)
		{
			m_pCapBuf = new BYTE[dwSize];
			if (m_pCapBuf == NULL)
			{
				return;
			}
		}

		//抓图BMP图片
		bFlag = PlayM4_GetJPEG(m_lPort[lRealPlayHandle], m_pCapBuf, dwSize, &dwCapSize);
		if (bFlag == FALSE)
		{
			dwErr = PlayM4_GetLastError(m_lPort[lRealPlayHandle]);
			printf("PlayM4_GetLastError, error code: %d\n", dwErr);
			break;
		}
		if (bFlag) {
			FILE* fp = NULL;
			time_t timep;
			time(&timep); //获取从1970至今过了多少秒，存入time_t类型的timep
			std::string temp_str = std::to_string(timep) + ".jpg";
			fp = fopen(temp_str.c_str(), "wb");
			// 将字符数组写入文件,文件即为图片文件
			fwrite(m_pCapBuf, sizeof(char), dwCapSize, fp); // 不包括末尾的空字符
			// 关闭文件
			fclose(fp);

		}

		if (m_pCapBuf != NULL)
		{
			delete[] m_pCapBuf;
			m_pCapBuf = NULL;
		}
		printf("完成第%d张抓图\n", i);
		//等待1秒后进下下一次抓图
		sleep(1);
	}
}

//sdk码流回调
void CALLBACK g_RealDataCallBack_V30(LONG lRealHandle, DWORD dwDataType, BYTE* pBuffer, DWORD dwBufSize, void* dwUser)
{
	DWORD dRet = 0;
	BOOL inData = FALSE;
	LONG lPort = -1;
	switch (dwDataType)
	{
	case NET_DVR_SYSHEAD: //系统头

		if (!PlayM4_GetPort(&lPort))  //获取播放库未使用的通道号
		{
			printf("申请播放库资源失败");
			break;
		}
		printf("播放库句柄：%d\n", lPort);
		m_lPort[lRealPlayHandle] = lPort; //第一次回调的是系统头，将获取的播放库port号赋值给全局port，下次回调数据时即使用此port号播放

		if (dwBufSize > 0){
		
			//设置实时流播放模式
			if (!PlayM4_SetStreamOpenMode(m_lPort[lRealPlayHandle], STREAME_REALTIME))
			{
				printf("PlayM4_SetStreamOpenMode Error\n");
				printf("GetLastError错误码 :%d\n", PlayM4_GetLastError(m_lPort[lRealPlayHandle]));
				break;
			}
			else
			{
				printf("PlayM4_SetStreamOpenMode Sus!\n");
			}
			//打开流接口
			if (!PlayM4_OpenStream(m_lPort[lRealPlayHandle], pBuffer, dwBufSize, 5*1024 * 1024))
			{
				printf("PlayM4_OpenStream Error\n");
				printf("GetLastError错误码 :%d\n", PlayM4_GetLastError(m_lPort[lRealPlayHandle]));
				break;
			}
			else
			{
				printf("PlayM4_OpenStream Sus!\n");
			}
			//设置解码模式，第二个参数0为软解码，1为硬解码（硬解码需要硬件支持）
			/*if (!PlayM4_SetDecodeEngine(m_lPort[lRealPlayHandle], 1))
			{
				printf("PlayM4_SetDecodeEngine Error\n");
				printf("GetLastError错误码 :%d\n", PlayM4_GetLastError(m_lPort[lRealPlayHandle]));
				break;
			}
			else
			{
				printf("PlayM4_SetDecodeEngine Sus!\n");
			}
			//设置硬解码回调，若设置为硬解码模式，需要使用该接口设置硬解码回调
			if (!PlayM4_SetDisplayCallBackYUV(m_lPort[lRealPlayHandle], DisplayCBFun, FALSE, NULL))
			{
				printf("PlayM4_SetDisplayCallBackYUV Error\n");
				printf("GetLastError错误码 :%d\n", PlayM4_GetLastError(m_lPort[lRealPlayHandle]));
				break;
			}
			else
			{
				printf("PlayM4_SetDecodeEngine Sus!\n");
			}*/
			

			//设置解码回调函数 解码显示	回调yuv数据，软解模式下，使用该回调			
			if (!PlayM4_SetDecCallBackExMend(m_lPort[lRealPlayHandle], DecCBFunIm, NULL, 0, NULL))
			{
				printf("PlayM4_SetDecCallBackExMend Error\n");
				printf("GetLastError错误码 :%d\n", PlayM4_GetLastError(m_lPort[lRealPlayHandle]));
				break;
			}
			else
			{
				printf("PlayM4_SetDecodeEngine Sus!\n");
			}

			if (!PlayM4_Play(m_lPort[lRealPlayHandle],NULL)) 
			{
				printf("PlayM4_Play Error\n");
				printf("GetLastError错误码 :%d\n", PlayM4_GetLastError(m_lPort[lRealPlayHandle]));
				break;
			}
			else
			{
				printf("PlayM4_SetDecodeEngine Sus!\n");
			}
		}
		break;
	case NET_DVR_STREAMDATA:   //码流数据
		if (dwBufSize > 0 && m_lPort[lRealPlayHandle] != -1)
		{
			//送数据入播放库
			while (!PlayM4_InputData(m_lPort[lRealPlayHandle], pBuffer, dwBufSize))
			{

				int dwError = PlayM4_GetLastError(m_lPort[lRealPlayHandle]);
				printf("播放库句柄ID：%d,错误码：%d\n", m_lPort[lRealPlayHandle], dwError);
				if (dwError == 11)  //缓冲区满，需要重复送入数据
				{
					continue;
				}
			}
		}
		break;
	default: //其他数据
		if (dwBufSize > 0 && m_lPort[lRealPlayHandle] != -1)
		{
			if (!PlayM4_InputData(m_lPort[lRealPlayHandle], pBuffer, dwBufSize))
			{
				break;
			}
		}
		break;
	}

}
//*********************************
// 函数入口
//******************************************************************************
int main()
{
	// 初始化
	NET_DVR_Init();
	char ansiStringss[] = "./sdkLog";
	NET_DVR_SetLogToFile(3, ansiStringss, TRUE);
	//设置连接时间与重连时间
	NET_DVR_SetConnectTime(2000, 1);
	NET_DVR_SetReconnect(10000, true);

	// 注册设备句柄
	LONG lUserID;

	// 从配置文件读取设备信息 
	IniFile ini("Device.ini");
	unsigned int dwSize = 0;
	char sSection[16] = "DEVICE";

	
	char *sIP = ini.readstring(sSection, "ip", "error", dwSize);
	int iPort = ini.readinteger(sSection, "port", 0);
	char *sUserName = ini.readstring(sSection, "username", "error", dwSize); 
	char *sPassword = ini.readstring(sSection, "password", "error", dwSize);
	int iChannel = ini.readinteger(sSection, "channel", 0);

	
	//登录参数，包括设备地址、登录用户、密码等
	NET_DVR_USER_LOGIN_INFO struLoginInfo = { 0 };
	struLoginInfo.bUseAsynLogin = 0; //同步登录方式
	//struLoginInfo.sDeviceAddress = ini.readstring(sSection, "ip", "error", dwSize); //设备IP地址
	memcpy(struLoginInfo.sDeviceAddress, ini.readstring(sSection, "ip", "error", dwSize), NET_DVR_DEV_ADDRESS_MAX_LEN); //设备IP地址
	struLoginInfo.wPort = ini.readinteger(sSection, "port", 0); //设备服务端口
	//struLoginInfo.sUserName = ini.readstring(sSection, "username", "error", dwSize); //设备登录用户名
	memcpy(struLoginInfo.sUserName, ini.readstring(sSection, "username", "error", dwSize), NAME_LEN);
	//struLoginInfo.sPassword = ini.readstring(sSection, "password", "error", dwSize); //设备登录密码
	memcpy(struLoginInfo.sPassword, ini.readstring(sSection, "password", "error", dwSize), NAME_LEN);

	//设备信息, 输出参数
	NET_DVR_DEVICEINFO_V40 struDeviceInfoV40 = { 0 };
	//登录
	lUserID = NET_DVR_Login_V40(&struLoginInfo, &struDeviceInfoV40);
	if (lUserID < 0)
	{
		printf("Login failed, error code: %d\n", NET_DVR_GetLastError());
		NET_DVR_Cleanup();
		return 0;
	}

	//预览相关参数设置
	NET_DVR_PREVIEWINFO struPlayInfo = { 0 };
	struPlayInfo.hPlayWnd = NULL;         //需要SDK解码时句柄设为有效值，仅取流不解码时可设为空
	struPlayInfo.lChannel = ini.readinteger(sSection, "channel", 0);       //预览通道号
	struPlayInfo.dwStreamType = 0;       //0-主码流，1-子码流，2-码流3，3-码流4，以此类推
	struPlayInfo.dwLinkMode = 0;       //0- TCP方式，1- UDP方式，2- 多播方式，3- RTP方式，4-RTP/RTSP，5-RSTP/HTTP
	struPlayInfo.bBlocked = 1;       //0- 非阻塞取流，1- 阻塞取流

	//启动预览并设置回调数据流
	lRealPlayHandle = NET_DVR_RealPlay_V40(lUserID, &struPlayInfo, g_RealDataCallBack_V30, NULL);//

	if (lRealPlayHandle < 0)
	{
		printf("NET_DVR_RealPlay_V40 error %d\n", NET_DVR_GetLastError());
		NET_DVR_Logout(lUserID);
		NET_DVR_Cleanup();
		return 1;
	}
	//等待播放库有数据，否则后面无法使用播放库抓图
	sleep(3);

	// 创建并启动抓图线程
	std::thread t1(getPic);

	// 播放库抓图分离线程
	t1.detach();

	//等待继续预览秒
	sleep(20);

	//---------------------------------------
	//关闭预览
	NET_DVR_StopRealPlay(lRealPlayHandle);
	//释放播放库资源
	PlayM4_Stop(m_lPort[lRealPlayHandle]);
	//关闭流
	PlayM4_CloseStream(m_lPort[lRealPlayHandle]);
	//释放播放端口
	PlayM4_FreePort(m_lPort[lRealPlayHandle]);
	//退出登录
	NET_DVR_Logout(lUserID);
	//释放sdk资源
	NET_DVR_Cleanup();
	return 1;
}
