# 播放库编程指南 Linux V7.3.7

> 来源：`播放库编程指南_linux V7.3.7.chm`

## 目录

- 前言
  - [前言](#sec_001)
- 内容简介
  - [概述](#sec_003)
  - [系统要求](#sec_004)
- 版本更新
  - [更新记录](#sec_006)
- 编程导引
  - [SDK接口调用主要流程](#sec_008)
  - [倒放模块流程](#sec_009)
  - [流模式模块流程](#sec_010)
  - [同步回放模块流程](#sec_011)
  - [文件定位模块流程](#sec_012)
  - [文件模块流程](#sec_013)
  - [鱼眼模块流程](#sec_014)
  - [抓图模块流程](#sec_015)
- 基本接口定义
  - 系统操作及版本号说明
    - [PlayM4_GetSdkVersion](#sec_018)
  - 获取错误码
    - [PlayM4_GetLastError](#sec_020)
  - 播放库端口号
    - [PlayM4_GetPort](#sec_022)
    - [PlayM4_FreePort](#sec_023)
  - 文件操作
    - [PlayM4_OpenFile](#sec_025)
    - [PlayM4_CloseFile](#sec_026)
  - 流操作
    - [PlayM4_SetStreamOpenMode](#sec_028)
    - [PlayM4_GetStreamOpenMode](#sec_029)
    - [PlayM4_OpenStream](#sec_030)
    - [PlayM4_CloseStream](#sec_031)
    - [PlayM4_InputData](#sec_032)
    - [PlayM4_OpenStreamAdvanced](#sec_033)
  - 播放控制
    - [PlayM4_Play](#sec_035)
    - [PlayM4_Stop](#sec_036)
    - [PlayM4_Pause](#sec_037)
    - [PlayM4_Slow](#sec_038)
    - [PlayM4_Fast](#sec_039)
    - [PlayM4_OneByOne](#sec_040)
    - [PlayM4_OneByOneBack](#sec_041)
    - [PlayM4_PlaySound](#sec_042)
    - [PlayM4_StopSound](#sec_043)
    - [PlayM4_PlaySoundShare](#sec_044)
    - [PlayM4_StopSoundShare](#sec_045)
    - [PlayM4_SetVolume](#sec_046)
    - [PlayM4_GetVolume](#sec_047)
    - [PlayM4_AdjustWaveAudio](#sec_048)
    - [PlayM4_SetColor](#sec_049)
    - [PlayM4_GetColor](#sec_050)
    - [PlayM4_SetImageSharpen](#sec_051)
    - [PlayM4_SetRotateAngle](#sec_052)
    - [PlayM4_GetCurrentFrameRate](#sec_053)
    - [PlayM4_GetFileHeadLength](#sec_054)
    - [PlayM4_GetFileTime](#sec_055)
    - [PlayM4_GetFileTotalFrames](#sec_056)
    - [PlayM4_GetPictureSize](#sec_057)
    - [PlayM4_GetPlayedFrames](#sec_058)
    - [PlayM4_GetPlayedTime](#sec_059)
    - [PlayM4_GetSpecialData](#sec_060)
    - [PlayM4_GetSystemTime](#sec_061)
  - 文件定位
    - [PlayM4_GetPlayPos](#sec_063)
    - [PlayM4_SetPlayPos](#sec_064)
    - [PlayM4_SetPlayedTimeEx](#sec_065)
    - [PlayM4_GetPlayedTimeEx](#sec_066)
    - [PlayM4_SetCurrentFrameNum](#sec_067)
    - [PlayM4_GetCurrentFrameNum](#sec_068)
    - [PlayM4_GetMpOffset](#sec_069)
  - 获取播放或解码信息
    - [PlayM4_SetDecCBStream](#sec_071)
    - [PlayM4_SetDecodeFrameType](#sec_072)
    - [PlayM4_SetDecCallBackMend](#sec_073)
    - [PlayM4_SetDecCallBackExMend](#sec_074)
    - [PlayM4_SetFileEndCallback](#sec_075)
    - [PlayM4_SetEncTypeChangeCallBack](#sec_076)
    - [PlayM4_ThrowBFrameNum](#sec_077)
    - [PlayM4_CheckDiscontinuousFrameNum](#sec_078)
    - [PlayM4_SetCheckWatermarkCallBack](#sec_079)
    - [PlayM4_SetSecretKey](#sec_080)
    - [PlayM4_SetEncryptTypeCallBack](#sec_081)
    - [PlayM4_SetDecodeThreadNum](#sec_082)
    - [PlayM4_SetDecodeERC](#sec_083)
  - 显示操作
    - [PlayM4_SetDisplayRegion](#sec_085)
    - [PlayM4_SetDisplayRegionOnWnd](#sec_086)
    - [PlayM4_RefreshPlay](#sec_087)
    - [PlayM4_RefreshPlayEx](#sec_088)
    - [PlayM4_SetDisplayType](#sec_089)
    - [PlayM4_GetDisplayType](#sec_090)
    - [PlayM4_WndResolutionChange](#sec_091)
    - [PlayM4_DisplayLostFrames](#sec_092)
  - 缓冲区操作
    - 解码前源缓冲区
      - [PlayM4_GetSourceBufferRemain](#sec_095)
      - [PlayM4_SetSourceBufCallBack](#sec_096)
      - [PlayM4_ResetSourceBuffer](#sec_097)
    - 解码后播放缓冲区
      - [PlayM4_SetDisplayBuf](#sec_099)
      - [PlayM4_GetDisplayBuf](#sec_100)
    - 源、播放缓冲区
      - [PlayM4_ResetBuffer](#sec_102)
      - [PlayM4_ResetSourceBufFlag](#sec_103)
      - [PlayM4_GetBufferValue](#sec_104)
  - 文件索引
    - [PlayM4_SetFileRefCallBack](#sec_106)
    - [PlayM4_GetKeyFramePos](#sec_107)
    - [PlayM4_GetNextKeyFramePos](#sec_108)
    - [PlayM4_GetRefValue](#sec_109)
    - [PlayM4_GetRefValueEx](#sec_110)
    - [PlayM4_SetRefValue](#sec_111)
  - 抓图
    - [PlayM4_SetDisplayCallBack](#sec_113)
    - [PlayM4_SetDisplayCallBackEx](#sec_114)
    - [PlayM4_ConvertToBmpFile](#sec_115)
    - [PlayM4_ConvertToJpegFile](#sec_116)
    - [PlayM4_GetBMP](#sec_117)
    - [PlayM4_GetJPEG](#sec_118)
    - [PlayM4_SetJpegQuality](#sec_119)
  - 画图回调
    - [PlayM4_RegisterDrawFun](#sec_121)
  - 倒放功能
    - [PlayM4_ReversePlay](#sec_123)
  - 同步回放功能
    - [PlayM4_SetSycGroup](#sec_125)
    - [PlayM4_GetSupplementaryTimeZone](#sec_126)
    - [PlayM4_SetSupplementaryTimeZone](#sec_127)
  - 鱼眼功能
    - [PlayM4_FEC_Enable](#sec_129)
    - [PlayM4_FEC_Disable](#sec_130)
    - [PlayM4_FEC_GetPort](#sec_131)
    - [PlayM4_FEC_DelPort](#sec_132)
    - [PlayM4_FEC_SetParam](#sec_133)
    - [PlayM4_FEC_GetParam](#sec_134)
    - [PlayM4_FEC_SetWnd](#sec_135)
    - [PlayM4_FEC_SetCallBack](#sec_136)
    - [PlayM4_FEC_Capture](#sec_137)
    - [PlayM4_FEC_GetCurrentPTZPort](#sec_138)
    - [PlayM4_FEC_SetCurrentPTZPort](#sec_139)
    - [PlayM4_FEC_SetPTZOutLineShowMode](#sec_140)
    - [PlayM4_FEC_GetViewParam](#sec_141)
    - [PlayM4_FEC_SetViewParam](#sec_142)
    - [PlayM4_FEC_SetDisplayRegion](#sec_143)
    - [PlayM4_FEC_SetCorrectEffect](#sec_144)
    - [PlayM4_FEC_Set3DModelParam](#sec_145)
    - [PlayM4_FEC_GetSpecialViewParam](#sec_146)
  - 私有数据
    - [PlayM4_RenderPrivateData](#sec_148)
    - [PlayM4_RenderPrivateDataEx](#sec_149)
    - [PlayM4_GetStreamAdditionalInfo](#sec_150)
    - [PlayM4_SetConfigFontPath](#sec_151)
  - 解码和显示模式
    - [PlayM4_GetD3DCapture](#sec_153)
    - [PlayM4_GetD3DPostProcess](#sec_154)
    - [PlayM4_SetD3DPostProcess](#sec_155)
  - 其他功能
    - [PlayM4_SkipErrorData](#sec_157)
- 帮助
  - [常见问题解答](#sec_159)
- [封面（附录）](#sec_160)
- [PlayM4_GetPictureQuality（附录）](#sec_161)
- [PlayM4_GetTimerType（附录）](#sec_162)
- [PlayM4_SetDecCallBack（附录）](#sec_163)
- [PlayM4_SetDeflash（附录）](#sec_164)
- [PlayM4_SetPicQuality（附录）](#sec_165)
- [PlayM4_SetPlayMode（附录）](#sec_166)
- [PlayM4_SetPreRecordCallBack（附录）](#sec_167)
- [PlayM4_SetPreRecordFlag（附录）](#sec_168)
- [PlayM4_SetSycStartTime（附录）](#sec_169)
- [PlayM4_SetTimerType（附录）](#sec_170)
- [PlayM4_SyncToAudio（附录）](#sec_171)
- [AdditionDataInfo（附录）](#sec_172)
- [CROP_PIC_INFO（附录）](#sec_173)
- [CYCLEPARAM（附录）](#sec_174)
- [D3D_PIC_INFO（附录）](#sec_175)
- [DISPLAY_INFO（附录）](#sec_176)
- [ENCRYPT_INFO（附录）](#sec_177)
- [FECCOLOR（附录）](#sec_178)
- [FISHEYEPARAM（附录）](#sec_179)
- [FRAME_INFO（附录）](#sec_180)
- [FRAME_POS（附录）](#sec_181)
- [FRAME_TYPE（附录）](#sec_182)
- [PLAYM4_SESSION_INFO（附录）](#sec_183)
- [PLAYM4_SYSTEM_TIME（附录）](#sec_184)
- [PTZPARAM（附录）](#sec_185)
- [RECORD_DATA_INFO（附录）](#sec_186)
- [SYSTEMTIME（附录）](#sec_187)
- [WATERMARK_INFO（附录）](#sec_188)
- [预录模块流程（附录）](#sec_189)

---

<a id="sec_001"></a>
### 前言

前言

非常感谢您使用我们公司的产品，我们将竭诚为您提供最好的服务。

本手册可能包含技术上不准确的地方或文字错误。

本手册的内容将做定期的更新，恕不另行通知；更新的内容将会在本手册的新版本中加入。

我们随时会改进或更新本手册中描述的产品或程序。

<a id="sec_003"></a>
### 概述

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK开发编程指南 |

# 概述

海康威视播放库SDK（以下简称“播放库SDK”）是海康威视嵌入式网络硬盘录像机、视频服务器、IP设备的配套产品的播放相关的二次开发包，适用于海康基线编码产品数据流的解码与播放。

**播放库SDK主要功能**

主要用于实时码流预览、录像文件回放、播放控制（如：暂停、单帧前进、单帧后退）、获取码流基本信息（如：创建文件索引、解码帧信息、分辨率、帧率）、支持JPG和BMP两种格式的播放截图等。

**播放库SDK包括文件模式和流模式：**

**文件模式**

播放库SDK内部线程实现读取指定录像文件。

**流模式**

流模式是指将待解码的数据以流的方式送入到播放库缓冲区中进行解码。

  

**我们提供Linux版本的SDK。**

  

---

<a id="sec_004"></a>
### 系统要求

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK开发使用手册 |

# SDK支持的系统说明

**Linux 32位播放库：**

- GCC版本要求大于等于4.4.7
- 支持系统：Ubuntu12.04、centos6.5及以上版本

**Linux 64位播放库：**

- GCC版本要求大于等于4.4.7
- 支持系统：Ubuntu12.04、centos6.5及以上版本

---

<a id="sec_006"></a>
### 更新记录

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK开发编程指南 |

# 更新记录

 **7.3.7.x** build20190316 |

|  |
| --- |
| 更新原因： |
| 1.新增鱼眼功能接口:[PlayM4_FEC_GetViewParam](#sec_141)、 [PlayM4_FEC_SetViewParam](#sec_142)、 [PlayM4_FEC_SetDisplayRegion](#sec_143)、 [PlayM4_FEC_SetCorrectEffect](#sec_144)、 [PlayM4_FEC_Set3DModelParam](#sec_145)、 [PlayM4_FEC_GetSpecialViewParam](#sec_146)。 |
| 2.新增Mp4(3gp)索引前置文件流式获取播放时间对应的文件偏移位置:[PlayM4_GetMpOffset](#sec_069)。 |
| 3.新增同步回放码流时区接口:[PlayM4_SetSupplementaryTimeZone](#sec_127)、[PlayM4_GetSupplementaryTimeZone](#sec_126)。 |

# 更新记录

 **7.3.3.x** build20170624 |

|  |
| --- |
| 更新原因： |
| 1.新增窗口大小改变通知:[PlayM4_WndResolutionChange](#sec_091)。 |
| 2.新增私有信息显示:[PlayM4_RenderPrivateDataEx](#sec_149)，扩展PLAYM4_PRIDATA_RENDER宏定义：PLAYM4_RENDER_FIRE_DETCET（热成像信息）、PLAYM4_RENDER_TEM（温度信息）。新增宏定义PLAYM4_FIRE_ALARM和PLAYM4_TEM_FLAG |
| 3.新增鱼眼接口:[PlayM4_FEC_Capture](#sec_137)、[PlayM4_FEC_GetCurrentPTZPort](#sec_138)、[PlayM4_FEC_SetCurrentPTZPort](#sec_139)、[PlayM4_FEC_SetPTZOutLineShowMode](#sec_140)。 |
| 4.新增错误码:PLAYM4_FEC_ERR_PLACETYPE（安装方式不对.一个播放库port，对应一种安装方式）、PLAYM4_FEC_ERR_NULLWND（设置的鱼眼窗口hWnd为null或者鱼眼port的窗口更换）、PLAYM4_FEC_ERR_CorrectType（矫正方式已有,不能开多个,一个播放库port,除了PTZ,其他矫正方式只能开一路;且设置180度矫正时只能为单独的一路）。 |
| 5.新增设置字符叠加的字体库路径接口:[PlayM4_SetConfigFontPath](#sec_151)。 |

 **7.2.0.22** build20170524 |

|  |
| --- |
| 更新原因： |
| 1.修复mp2音频GPL版权问题。 |

 **V7.2.0.X** build20150403 |

|  |
| --- |
| 更新原因： |
| 1. 增加了鱼眼功能:[PlayM4_FEC_Enable](#sec_129)、[PlayM4_FEC_Disable](../接口定义/PlayM4_FEC_Disable .html) 、[PlayM4_FEC_GetPort](#sec_131)、[PlayM4_FEC_DelPort](#sec_132)、 [PlayM4_FEC_SetParam](#sec_133)、[PlayM4_FEC_GetParam](#sec_134)、 [PlayM4_FEC_SetWnd](#sec_135)、[PlayM4_FEC_SetCallBack](#sec_136)。 |
| 2. 添加了实时流的自适应播放功能。 |
| 3. 添加了实时流预录像功能。 |
| 4. 添加了智能信息开关功能。 |
| 5. 添加了多线程解码功能。 |
| 6. [PlayM4_SetPreRecordFlag](../接口定义/PlayM4_SetPreRecordFlag.html)、[PlayM4_SetPreRecordCallBack](#sec_167)：添加预录功能接口。 |
| 7. [PlayM4_RenderPrivateData](#sec_148)：显示智能信息开关接口。 |

 **7.0.3.X** build20121224 |

|  |
| --- |
| 更新原因： |
| 1.修改PS封装的文件，若有B帧情况定位不准确的缺陷。 |
| 2. 修改大文件创建索引不成功的缺陷。 |
| 3.添加对MPEG2视频格式的支持，以及G726音频编码格式的支持 。 |
| 4. 更新底层的解码库。 |
| 5. 修正音频残留的缺陷。 |
| 6. 修正多通道播放时声音崩溃缺陷。 |

 **V7.0.0.X** build20120405 |

|  |
| --- |
| 更新原因： |
| 1. 视频显示使用opengl，音频播放使用openal,请确保响应的驱动安装正常。 |
| 2. 该版本暂不支持多个监视器下辅屏上的显示。 |

  

---

<a id="sec_008"></a>
### SDK接口调用主要流程

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# SDK接口调用的主要流程

![](images/基本框架.JPG)

其中虚线框的流程是可选部分，不会影响其他流程和模块的功能使用。按实现功能的不同可以分成上述几个模块，实现每个模块的功能时获取播放库端口号、打开文件/打开数据流、解码和释放SDK资源这4个流程是必不可少的。  
  

- 获取播放库端口号（[PlayM4_GetPort](#sec_022)）：获取播放端口号，内存预分配等操作。
- 打开待播放的文件（[PlayM4_OpenFile](#sec_025)）/数据流（[PlayM4_OpenStream](#sec_030)）：这部分用于打开待播放的文件或者实时数据流，
  此时会对打开的文件进行判断是否是播放库支持的文件，若是实时流模式则打开数据流部分需要送入正确的海康媒体信息头。
- 设置解码回调函数（[PlayM4_SetDecCallBack](#sec_163)或[PlayM4_SetDecCallBackExMend](#sec_074)）：
  获取解码后的音视频数据，当前播放库支持的视频解码后格式为YV12格式，音频解码后的格式为PCM格式数据。若客户需要其他格式的数据，则需要自行实现转换。
- 注册抓图回调函数（[PlayM4_SetDisplayCallBack](#sec_113)）：设置显示回调，获取解码后送入到显卡显示的当前视频帧数据。
- 开始解码（[PlayM4_Play](#sec_035)）：开始解码线程，若需要显示，则送入有效的窗口句柄，若不需要显示则可以将窗口句柄置为NULL，设置为NULL时候不影响正常解码。
- 文件模式模块：打开待解码的文件，开始解码并显示。以及获取解码后的音视频数据、定位和抓图等功能。具体流程详见[文件模块流程](文件模块流程.html)。
- 流模式模块  ：打开待解码的实时流数据，开始解码并显示。以及获取解码后的音视频数据、抓图回调抓图等功能。具体流程详见[流模式模块流程](流模式模块流程.html)。
- 倒放模块    ：倒放模块流程。具体流程详见[倒放模块流程](倒放模块流程.html)。
- 鱼眼控制模块：实现鱼眼的控制。具体流程详见[鱼眼模块流程](鱼眼模块流程.html)。
- 同步回放模块：实现多个文件同步回放的接口调用流程。具体流程详见[同步回放模块流程](同步回放模块流程.html)。
- 文件定位模块：文件播放后按照时间或者帧号进行定位的流程。具体流程详见[文件定位模块流程](文件定位模块流程.html)。
- 画图回调模块：实现对当前解码的图像上叠加客户设定的线框或者字符等，Linux版本播放库不支持该功能模块。具体流程详见[画图回调模块流程](画图回调模块流程.html)。
- 抓图模块    ：实现将对当前解码的视频帧抓取为BMP或者JPEG图片。具体流程详见[抓图模块流程](抓图模块流程.html)。
- 预录模块    ：实现将设备通过网络传输过来的码流转换为PS封装，然后通过回调函数给用户，方便用户保存为本地文件查看。具体流程详见[预录模块流程](预录模块流程.html)。

  
**注：本手册下文提供的代码都是在VC环境下编译的。**

---

<a id="sec_009"></a>
### 倒放模块流程

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# 倒放模块流程

![](images/文件倒放模块流程图.JPG)

  
  

正常播放是指按照时间顺序播放，倒放需要调用如下接口[PlayM4_ReversePlay](#sec_123)  
  

- 开始倒放接口：开始当前通道的倒放。
- 获取当前播放帧的全局时间模块：获取当前播放帧的全局时间，调用的接口为[PlayM4_GetSystemTime](#sec_061)。
- 设置流播放起始帧模块：设置流播放起始帧。
- 流模式进行倒放，需要以GOP为单位，倒着送入到播放库中进行倒放。

#### 示例代码

文件模式倒放

```

#include <stdio.h>
#include <string.h>
#include <iostream>
#include "unistd.h"
#include "PlayM4.h"
using namespace std;

LONG g_lPort  =  -1;

HWND hWnd = 0;  //Linux系统如果使用Qt进行界面开发，可以获取窗口句柄

void CALLBACK FileRefDoneCB(DWORD nPort,DWORD nUser)
{
   TRACE("File reference created!\n");
}

void main() 
{
   BOOL   bFlag = FALSE;
   DWORD  dwErr = 0;

    if (g_lPort == -1)
    {
      bFlag = PlayM4_GetPort(&g_lPort);
      if (bFlag == FALSE)
      {
         dwErr = PlayM4_GetLastError(g_lPort);
         return;
       }
    }   

    PlayM4_SetFileRefCallBack(g_lPort,FileRefDoneCB,NULL);

    bFlag = PlayM4_OpenFile(g_lPort,"test.mp4");

    bFlag = PlayM4_Play(g_lPort,hWnd);

    PlayM4_ReversePlay(g_lPort);


    sleep(10000);

    PlayM4_Stop(g_lPort);

    PlayM4_CloseFile(g_lPort);

    PlayM4_FreePort(g_lPort);

    g_lPort = -1;

}
```

  

---

<a id="sec_010"></a>
### 流模式模块流程

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# 流模式模块流程

![](images/流模式模块流程图.JPG)  
  

- 流模式模块需要先获取播放库通道号，然后设置流模式（相关接口[PlayM4_GetPort](#sec_022)、[PlayM4_SetStreamOpenMode](#sec_028)），送入正确的海康媒体信息头打开数据流
  （相关接口[PlayM4_OpenStream](#sec_030)），开始解码播放（相关接口[PlayM4_Play](#sec_035)),然后送入正确的海康数据(相关接口[PlayM4_InputData](#sec_032))。
  
- 实时流需要获取解码后的数据，则可以调用解码回调接口（相关接口[PlayM4_SetDecCallBack](#sec_163)、[PlayM4_SetDecCallBackExMend](#sec_074)）。
- 多路实时流若都需要获取解码后的数据，每个需要获取解码数据的通道都可以调用解码回调接口（[PlayM4_SetDecCallBack](#sec_163)），在解码回调函数中根据nPort号判断是具体哪路数据。

#### 示例代码

示例一：流模式解码数据(以本地PC上的录像文件模拟实时流数据输入）

```

#include <stdio.h>
#include <iostream>
#include "iostream"
#include "unistd.h"
#include "PlayM4.h"
using namespace std;
LONG  g_nPort  = -1;
#define READ_BUF_SIZE 200
#define HIK_HEAD_LEN 40

HWND hWnd = 0;  //Linux系统如果使用Qt进行界面开发，可以获取窗口句柄

void CALLBACK DecCBFun(long nPort,char * pBuf,long nSize,
					   FRAME_INFO * pFrameInfo, 
					   long nReserved1,long /*nReserved2*/)
{
	
     //---------------------------------------
     // 获取解码后音频数据
     if (pFrameInfo->nType == T_AUDIO16)
     {
       printf("test:: get audio data !\n");
      }
```

```


     //---------------------------------------
     // 获取解码后视频数据
      else if ( pFrameInfo->nType == T_YV12 ) 
     {   
        printf("test:: get video data !\n");
      }
}


using namespace std;

void main() 
{
  BOOL bFlag    = FALSE;
  int  nError   = 0;
  FILE* fp      =  NULL;
  char* pBuffer = NULL;

  //---------------------------------------
  // 获取播放库通道号
  PlayM4_GetPort(&g_nPort);

  //打开待解码文件
  fp = fopen( "test.mp4", ("rb") );
  if (fp == NULL)
  {
     printf("cannot open the file !\n");
     return;
  }


  pBuffer = new char[READ_BUF_SIZE];
  if (pBuffer == NULL)
  {
    return;
  }

  //读取文件中海康文件头
  fread( pBuffer, HIK_HEAD_LEN, 1, fp );

  //设置流模式类型 
  PlayM4_SetStreamOpenMode(g_nPort,STREAME_FILE); 
  //打开流模式
  PlayM4_OpenStream(g_nPort,(PBYTE)pBuffer,HIK_HEAD_LEN,1024 * 1024);

  //设置解码回调
  PlayM4_SetDecCallBackExMend(g_nPort,DecCBFun,NULL,0,NULL);
     
  PlayM4_Play(g_nPort,hWnd);

  while (!feof(fp))
  {		
     fread( pBuffer, READ_BUF_SIZE, 1, fp );
	  
     while (1)
     {
       bFlag = PlayM4_InputData(g_nPort,(PBYTE)pBuffer,READ_BUF_SIZE);
       if (bFlag == FALSE)
       {
           nError = PlayM4_GetLastError(g_nPort);
			  
           //若缓冲区满，则重复送入数据
           if (nError == PLAYM4_BUF_OVER)
          {
	      Sleep(2);
	      continue;
           }
        }
		  
        //若送入成功，则继续读取数据送入到播放库缓冲
        break; 
      }
  }


  Sleep(10000);
  //---------------------------------------
  // 停止解码
   PlayM4_Stop(g_nPort);
   
   //关闭流，回收源数据缓冲
   PlayM4_CloseStream(g_nPort);

   //释放播放库端口号
   PlayM4_FreePort(g_nPort);

   if (fp != NULL)
   {
        fclose(fp);
        fp = NULL;
   }


  if (pBuffer != NULL)
  {
    delete [] pBuffer;
    pBuffer = NULL;
  }
  return;
}




```

#### Remarks

由于文件流送数据较快，如果文件流按实时流模式播放，也有可能出现快放慢放的效果。

---

<a id="sec_011"></a>
### 同步回放模块流程

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# 同步回放模块流程

![](images/同步回放模块流程图.JPG)

  
  

同步回放是指多个文件在有相同的时间段，然后多个窗口按照相同的时间戳播放。其中需要调用接口（[PlayM4_SetSycGroup](#sec_125)、[PlayM4_SetSycStartTime](#sec_169)）。

  

#### 示例代码

示例一：同步回放

```

#include <stdio.h>
#include <iostream>
#include "SynPlayMode.h"
#include "SynPlayModeDlg.h"
#include "PlayM4.h
#include "unistd.h"
using namespace std;

long m_lPort1 = -1;
long m_lPort2 = -1;
BOOL bFlag = FALSE;
HWND hWnd = 0;
HWND hWnd1 = 0;

void main() {

  //---------------------------------------
  // 获取播放库端口号
  bFlag = PlayM4_GetPort(&m_lPort1);
  bFlag = PlayM4_GetPort(&m_lPort2);

  //打开待播放文件
  bFlag = PlayM4_OpenFile(m_lPort1,"file1.mp4");
  bFlag = PlayM4_OpenFile(m_lPort2,"file2.mp4");

  //---------------------------------------
  //设置同步回放
  bFlag =	PlayM4_SetSycGroup(m_lPort1,0);
  bFlag =	PlayM4_SetSycGroup(m_lPort2,0);

  //如果使用Qt进行界面开发，获取窗口句柄
  //HWND hWnd = (HWND)m_framePlayWnd->GetPlayWndId();
  //HWND hWnd1 = (HWND)m_framePlayWnd1->GetPlayWndId();

  //开始播放
   PlayM4_Play(m_lPort1,hWnd);
   PlayM4_Play(m_lPort2,hWnd1);
  
  sleep(10000);
  
  //停止播放
   PlayM4_Stop(m_lPort1);
   PlayM4_Stop(m_lPort2);

  //关闭文件
  PlayM4_CloseFile(m_lPort1);
  PlayM4_CloseFile(m_lPort2);

  //释放播放库端口
  PlayM4_FreePort(m_lPort1);
  m_lPort1 = -1;

  PlayM4_FreePort(m_lPort2);
  m_lPort2 = -1;

  return;
}

```

  

---

<a id="sec_012"></a>
### 文件定位模块流程

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# 文件定位模块流程

  

![](images/文件定位模块流程图.jpg)

播放本地PC上的录像文件，播放库SDK支持按照帧号或者时间对文件进行定位，流程如下：

- 先获取播放库端口号（[PlayM4_GetPort](#sec_022)）；- 打开待播放的文件（[PlayM4_OpenFile](#sec_025)）；- 创建文件索引（[PlayM4_SetFileRefCallBack](#sec_106)）；- 开始播放解码（[PlayM4_Play](#sec_035)）；- 按照时间或者帧号进行定位（[PlayM4_SetCurrentFrameNum](#sec_067)、[PlayM4_SetPlayPos](#sec_064)、[PlayM4_SetPlayedTimeEx](#sec_065)）；

          定位实现：
          - 创建文件索引（[PlayM4_SetFileRefCallBack](#sec_106)）。- 设置当前帧号（[PlayM4_SetCurrentFrameNum](#sec_067)），或者设定当前播放位置（[PlayM4_SetPlayPos](#sec_064)），设置当前播放时间（[PlayM4_SetPlayedTimeEx](#sec_065)）。

          #### 示例代码

          播放文件

          ```
          
          #include <stdio.h>
          #include <iostream>
          #include "unistd.h"
          #include "PlayM4.h"
          using namespace std;
          LONG nPort = -1;
          BOOL bFlag = FALSE;
          BOOL g_bRefDone= FALSE;
          using namespace std;
          
          HWND hWnd = 0;  //Linux系统如果使用Qt进行界面开发，可以获取窗口句柄
          
          void CALLBACK FileRefDoneCB(DWORD nPort,DWORD nUser)
          {
                 g_bRefDone = TRUE;
          	TRACE("File reference created!\n");
          }
          void main() 
          {	
              //---------------------------------------
              // 获取播放库端口号
              bFlag = PlayM4_GetPort(&nPort);
          	
             //---------------------------------------
              // 创建文件索引
              PlayM4_SetFileRefCallBack(nPort,FileRefDoneCB,NULL);
          
              //打开待播放的文件
              bFlag = PlayM4_OpenFile(nPort,"test.mp4");
              if (bFlag == FALSE)
              {
          	int nErr = PlayM4_GetLastError(nPort);
          	printf("Open file failed %d!",nErr);
          	return;
              }
          	
            //开始播放文件
              PlayM4_Play(nPort, hWnd);
          	
          	
              while (1)
             {
                if (g_bRefDone == FALSE)
                {
                     Sleep(2);
                     continue;
                 }
                 else//索引创建成功
                 {
                    break;
                  }
              }
          
             //定位到帧号为20的视频位置
             PlayM4_SetCurrentFrame(nPort,20);
             
             //定位到为2s的视频位置(从文件开始播放计时，播放2s的位置，即相对时间）
             PlayM4_SetPlayedTimeEx(nPort,2000);
          
             //定位到为5s的视频位置(从文件开始播放计时，播放5s的位置，即相对时间）
             PlayM4_SetPlayedTime(nPort,5);
             Sleep(10000);
          
          
          	
              //停止播放
              PlayM4_Stop(nPort);
              
              //停止播放声音
              PlayM4_StopSound();
          	
              //关闭文件
              PlayM4_CloseFile(nPort);
          	
              PlayM4_FreePort(nPort);
              nPort  =  -1;
          
              return;
          }
          
          ```

          ---

<a id="sec_013"></a>
### 文件模块流程

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# 文件模块流程

![](images/文件模块流程图.JPG)  
  

实现文件模块需要先获取播放库端口号，且需要确认文件是海康设备的录像文件。

  
  

#### 示例代码

播放文件

```

#include <stdio.h>
#include <iostream>
#include "unistd.h"
#include "PlayM4.h"
using namespace std;
LONG nPort = -1;
BOOL bFlag = FALSE;
using namespace std;

HWND hWnd = 0;  //Linux系统如果使用Qt进行界面开发，可以获取窗口句柄

void main() 
{	
    //---------------------------------------
    // 获取播放库端口号
    bFlag = PlayM4_GetPort(&nPort);
	
	
    //打开待播放的文件
    bFlag = PlayM4_OpenFile(nPort,"test.mp4");
    if (bFlag == FALSE)
    {
	int nErr = PlayM4_GetLastError(nPort);
	printf("Open file failed %d!",nErr);
	return;
    }
	
  //开始播放文件
    PlayM4_Play(nPort, hWnd);
	
    //播放声音
    PlayM4_PlaySound(nPort);	
	
    Sleep(10000);
	
    //停止播放
    PlayM4_Stop(nPort);
    
    //停止播放声音
    PlayM4_StopSound();
	
    //关闭文件
    PlayM4_CloseFile(nPort);
	
    PlayM4_FreePort(nPort);
    nPort  =  -1;

    return;
}

```

---

<a id="sec_014"></a>
### 鱼眼模块流程

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# 鱼眼模块流程

![](images/鱼眼模块流程图.JPG)

  
  

鱼眼功能模块是对鱼眼摄像机图像的矫正，使用时需要开启预览模块、获取鱼眼矫正处理子端口、设置鱼眼矫正参数、设置显示窗口、设置鱼眼窗口的绘图回调。  
  

- 开启和关闭鱼眼模块：开启鱼眼模块基本参数，调用的接口[PlayM4_FEC_Enable](#sec_129)、[PlayM4_FEC_Disable](#sec_130)。
- 获取/删除鱼眼矫正处理子端口：调用的接口有[PlayM4_FEC_GetPort](#sec_131)、[PlayM4_FEC_DelPort](#sec_132)。
- 设置/获取鱼眼矫正参数：调用的接口有[PlayM4_FEC_SetParam](#sec_133)、[PlayM4_FEC_GetParam](#sec_134)。
- 设置显示窗口：调用的接口有[PlayM4_FEC_SetWnd](#sec_135)。
- 设置鱼眼窗口画图回调：调用的接口有[PlayM4_FEC_SetCallBack](#sec_136) 。
- 设置鱼眼硬解码或者球面鱼眼时需要设置[PlayM4_FEC_SetConfig](../接口定义/PlayM4_FEC_SetConfig.html)接口；软解码开启鱼眼时则不需要设置此接口；

#### 示例代码

示例：鱼眼模块流程

```

#include <stdio.h>
#include <iostream>
#include "stdafx.h"
#include "SynPlayMode.h"
#include "SynPlayModeDlg.h"
#include "PlayM4.h
#include "Windows.h"
void FisheyePlay() 
{
	BOOL bRet = FALSE;
	FISHEYEPARAM stFEPara1 = {0};
	FISHEYEPARAM stFEPara2 = {0};
	FISHEYEPARAM stFEPara3 = {0};

         //获取播放库端口
	PlayM4_GetPort(&m_lPort);
	if (-1 == m_lPort)
	{
           CString str;
           str.Format("PlayM4_GetPort fail\n");	
           MessageBox(str);
           return;
	}

         //打开待播放的文件
	if (FALSE == PlayM4_OpenFile(m_lPort,m_strFileName.GetBuffer(m_strFileName.GetLength())))
	{
           CString str;
           str.Format("PlayM4_OpenFile fail[0x%x]\n",PlayM4_GetLastError(m_lPort));
           MessageBox(str);
           goto EXIT1;
	}

          //播放视频文件
	if (FALSE == PlayM4_Play(m_lPort,GetDlgItem(IDC_FISHEYE_MAIN_WND)->GetSafeHwnd()))
	{
           CString str;
           str.Format("PlayM4_Play fail[0x%x]\n",PlayM4_GetLastError(m_lPort));
           MessageBox(str);
           goto EXIT2;
	}

	//启动鱼眼功能
	if (FALSE == PlayM4_FEC_Enable(m_lPort))
	{
           CString str;
           str.Format("PlayM4_FEC_Enable fail[0x%x]\n",PlayM4_GetLastError(m_lPort));
           MessageBox(str);
           goto EXIT2;
	}

	//子端口1 顶装，PTZ矫正，获取鱼眼矫正处理子端口
	if (FALSE == PlayM4_FEC_GetPort(m_lPort,&m_nSubPort1,FEC_PLACE_CEILING,FEC_CORRECT_PTZ))
	{
            CString str;
            str.Format("PlayM4_FEC_GetPort1 fail[0x%x]\n",PlayM4_GetLastError(m_lPort));
            MessageBox(str);
            goto EXIT3;
	}

	//更新位置和Zoom值
	stFEPara1.nUpDateType = FEC_UPDATE_PTZPARAM | FEC_UPDATE_PTZZOOM;//更新的类型
	stFEPara1.stPTZParam.fPTZPositionX = 0.2; //PTZ显示的中心坐标
	stFEPara1.stPTZParam.fPTZPositionY = 0.3; //
	stFEPara1.fZoom                    = 0.1; //PTZ显示的范围参数
	//stCycleParam 用于圆心对当前鱼眼所有子端口都有影响

          //设置鱼眼矫正参数
	if (FALSE == PlayM4_FEC_SetParam(m_lPort,m_nSubPort1,&stFEPara1))
	{
            CString str;
            str.Format("PlayM4_FEC_SetParam1 fail[0x%x]\n",PlayM4_GetLastError(m_lPort));		
            MessageBox(str);
            goto EXIT3;
	}


	//子端口2 顶装，PTZ矫正 获取鱼眼矫正处理子端口
	if (FALSE == PlayM4_FEC_GetPort(m_lPort,&m_nSubPort2,FEC_PLACE_CEILING,FEC_CORRECT_PTZ))
	{
            CString str;
            str.Format("PlayM4_FEC_GetPort2 fail[0x%x]\n",PlayM4_GetLastError(m_lPort));	
            MessageBox(str);
            goto EXIT3;
	}
	
	//更新位置
	stFEPara2.nUpDateType = FEC_UPDATE_PTZPARAM;
	stFEPara2.stPTZParam.fPTZPositionX = 0.7; //(0,1)
	stFEPara2.stPTZParam.fPTZPositionY = 0.8; //(0,1)
    
        //设置鱼眼参数	
	if (FALSE == PlayM4_FEC_SetParam(m_lPort,m_nSubPort2,&stFEPara2))
	{
            CString str;
            str.Format("PlayM4_FEC_SetParam2 fail[0x%x]\n",PlayM4_GetLastError(m_lPort));		
            MessageBox(str);
            goto EXIT3;
	}


	//Zoom
	stFEPara3.nUpDateType = FEC_UPDATE_PTZZOOM;
	stFEPara3.fZoom                    = 0.9; //(0,1)
	
        //设置鱼眼参数
	if (FALSE == PlayM4_FEC_SetParam(m_lPort,m_nSubPort2,&stFEPara3))
	{
          CString str;
          str.Format("PlayM4_FEC_SetParam3 fail[0x%x]\n",PlayM4_GetLastError(m_lPort));
          MessageBox(str);
          goto EXIT3;
	}

	//add
	//子端口3 顶装，PTZ矫正 获取鱼眼矫正处理子端口
	if (FALSE == PlayM4_FEC_GetPort(m_lPort,&m_nSubPort3,FEC_PLACE_CEILING,FEC_CORRECT_PTZ))
	{
          CString str;
          str.Format("PlayM4_FEC_GetPort2 fail[0x%x]\n",PlayM4_GetLastError(m_lPort));		
          MessageBox(str);
          goto EXIT3;
	}
	

        //设置鱼眼参数
	stFEPara3.nUpDateType = FEC_UPDATE_PTZPARAM;
	stFEPara3.stPTZParam.fPTZPositionX = 0.7; //(0,1)
	stFEPara3.stPTZParam.fPTZPositionY = 0.8; //(0,1)
	stFEPara3.fZoom                    = 0.9; //(0,1)
	
	if (FALSE == PlayM4_FEC_SetParam(m_lPort,m_nSubPort2,&stFEPara3))
	{
          CString str;
          str.Format("PlayM4_FEC_SetParam3 fail[0x%x]\n",PlayM4_GetLastError(m_lPort));	
          MessageBox(str);
          goto EXIT3;
	}
	
	
	//设置鱼眼参数
	stFEPara3.nUpDateType = FEC_UPDATE_PTZZOOM;
	if (FALSE == PlayM4_FEC_SetParam(m_lPort,m_nSubPort2,&stFEPara3))
	{
          CString str;
          str.Format("PlayM4_FEC_SetParam3 fail[0x%x]\n",PlayM4_GetLastError(m_lPort));	
          MessageBox(str);
          goto EXIT3;
	}

    //设置显示窗口
	PlayM4_FEC_SetWnd(m_lPort,m_nSubPort1,GetDlgItem(IDC_FISHEYE_SUB_WND1)->GetSafeHwnd());
	PlayM4_FEC_SetWnd(m_lPort,m_nSubPort2,GetDlgItem(IDC_FISHEYE_SUB_WND2)->GetSafeHwnd());
	PlayM4_FEC_SetWnd(m_lPort,m_nSubPort3,GetDlgItem(IDC_FISHEYE_SUB_WND3)->GetSafeHwnd());

	return;

EXIT3:
    //删除鱼眼子端口
	if (-1 != m_nSubPort1)
	{
          PlayM4_FEC_DelPort(m_lPort,m_nSubPort1);
          m_nSubPort1 = -1;
	}

      //删除鱼眼子端口
	if (-1 != m_nSubPort2)
	{
           PlayM4_FEC_DelPort(m_lPort,m_nSubPort2);
           m_nSubPort2 = -1;
	}
    
      //删除鱼眼子端口
	if (-1 != m_nSubPort3)
	{
           PlayM4_FEC_DelPort(m_lPort,m_nSubPort3);
           m_nSubPort3 = -1;
	}	

    //关闭鱼眼模块
	PlayM4_FEC_Disable(m_lPort);

EXIT2:
	PlayM4_CloseFile(m_lPort);
EXIT1:
	if (-1 != m_lPort)
	{
           PlayM4_FreePort(m_lPort);
           m_lPort = -1;
	}
}
```

  

---

<a id="sec_015"></a>
### 抓图模块流程

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程导引 |

# 抓图模块流程

![](images/抓图模块流程图.JPG)

  
  

抓图模块适用于获取当前解码后送入到显卡显示的数据（解码后的数据）功能。该模块的所有功能都需要先进行注册显示回调，[PlayM4_SetDisplayCallBack](#sec_113)、[PlayM4_SetDisplayCallBackEx](#sec_114)。  

回调函数中不能调用参数有端口号的接口，所以只能调用PlayM4_ConvertToBmpFile 和PlayM4_ConvertToJpegFile ：调用的接口有
[PlayM4_ConvertToBmpFile](#sec_115)、[PlayM4_ConvertToJpegFile](#sec_116)

#### 示例代码

文件模式抓图（连续抓图和手动抓图）

```

#include <stdio.h>
#include <string.h>
#include <iostream>
#include "unistd.h"
#include "PlayM4.h"
using namespace std;

LONG     g_lPort                =  -1;
CString  m_strCapPicPath        = _T("");
CString  sFilePath              = _T("");
UINT	   m_npic_bmp             = 0;

HWND hWnd = 0;  //Linux系统如果使用Qt进行界面开发，可以获取窗口句柄

void CALLBACK DisplayCBFun(long nPort,char * pBuf,long nSize,long nWidth,long nHeight,long nStamp,long nType,long nReserved)
{
	TRACE("zytest: get vid pic !\n");

	if(m_strCapPicPath.Compare(""))
	{
         sFilePath.Format("%s\\capture%02d.bmp", "g:\\", m_npic_bmp++);
	}
	else
	{
         sFilePath.Format("C:\\capture%02d.bmp", m_npic_bmp++);
	}

	//连续抓BMP图片
	PlayM4_ConvertToBmpFile(pBuf,nSize,nWidth,nHeight,nType,sFilePath.GetBuffer(sFilePath.GetLength()));
}

void main() 
{
   	BOOL   bFlag          = FALSE;
	DWORD  dwErr          = 0;
	LONG dwWidth          = 0;
	LONG dwHeight         = 0;
	DWORD dwSize          = 0;
	DWORD dwCapSize       = 0;

    //获取播放库端口号
      if (g_lPort == -1)
      {
          bFlag = PlayM4_GetPort(&g_lPort);
          if (bFlag == FALSE)
          {
               dwErr = PlayM4_GetLastError(g_lPort);
               return;
           }
        }

    //打开待播放的文件
    bFlag = PlayM4_OpenFile(g_lPort,"test.mp4");

    //设置显示回调
    PlayM4_SetDisplayCallBack(g_lPort,DisplayCBFun);

    //解码显示
    bFlag = PlayM4_Play(g_lPort,hWnd);


    sleep(10000);

    //获取当前视频文件的分辨率
    bFlag  = PlayM4_GetPictureSize(g_lPort,&dwWidth,&dwHeight);
    dwSize = dwWidth * dwHeight * 5;
	
    //申请抓图内存
    if (m_pCapBuf == NULL)
    {
          m_pCapBuf = new BYTE[dwSize];
          if (m_pCapBuf == NULL)
          {
                return;
           }
      }

    //抓图BMP图片
    bFlag = PlayM4_GetBMP(g_lPort,m_pCapBuf,dwSize,&dwCapSize);
    if (bFlag == FALSE)
    {
         dwErr = PlayM4_GetLastError(m_lPort);
     }


    
    if (m_pCapBuf != NULL)
    {
        delete [] m_pCapBuf;
        m_pCapBuf = NULL;
    }

    //停止解码
    PlayM4_Stop(g_lPort);

    //关闭文件
    PlayM4_CloseFile(g_lPort);

    //释放端口号
    PlayM4_FreePort(g_lPort);

     g_lPort = -1;

}
```

  

---

<a id="sec_018"></a>
#### PlayM4_GetSdkVersion

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_GetSdkVersion

获取播放库SDK版本号和build号。

```
unsigned int  PlayM4_GetSdkVersion(
);
```

#### Parameters

*无*

#### Return Values

高16位表示当前的build号。9~16位表示主版本号，1~8位表示次版本号。如：返回值0x06040105表示：build号是0604，版本号1.5。

#### Remarks

如果只是修改bug，我们只升级后面两位版本号。

---

<a id="sec_020"></a>
#### PlayM4_GetLastError

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_GetLastError

获取错误号。

```
unsigned int PlayM4_GetLastError(
  int   nPort
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

播放库错误码：

| **错误类型** | 错误值 | 错误信息 |
| --- | --- | --- |
| **PLAYM4_NOERROR** | 0 | 没有错误； |
| **PLAYM4_PARA_OVER** | 1 | 输入参数非法； |
| **PLAYM4_ORDER_ERROR** | 2 | 调用顺序不对； |
| **PLAYM4_TIMER_ERROR** | 3 | 多媒体时钟设置失败； |
| **PLAYM4_DEC_VIDEO_ERROR** | 4 | 视频解码失败； |
| **PLAYM4_DEC_AUDIO_ERROR** | 5 | 音频解码失败； |
| **PLAYM4_ALLOC_MEMORY_ERROR** | 6 | 分配内存失败； |
| **PLAYM4_OPEN_FILE_ERROR** | 7 | 文件操作失败； |
| **PLAYM4_CREATE_OBJ_ERROR** | 8 | 创建线程事件等失败； |
| **PLAYM4_CREATE_DDRAW_ERROR** | 9 | 创建DierctDraw失败； |
| **PLAYM4_CREATE_OFFSCREEN_ERROR** | 10 | 创建后端缓存失败； |
| **PLAYM4_BUF_OVER** | 11 | 缓冲区满，输入流失败； |
| **PLAYM4_CREATE_SOUND_ERROR** | 12 | 创建音频设备失败； |
| **PLAYM4_SET_VOLUME_ERROR** | 13 | 设置音量失败； |
| **PLAYM4_SUPPORT_FILE_ONLY** | 14 | 只能在播放文件时才能使用此接口； |
| **PLAYM4_SUPPORT_STREAM_ONLY** | 15 | 只能在播放流时才能使用此接口； |
| **PLAYM4_SYS_NOT_SUPPORT** | 16 | 不支持； |
| **PLAYM4_FILEHEADER_UNKNOWN** | 17 | 没有文件头； |
| **PLAYM4_VERSION_INCORRECT** | 18 | 解码器和编码器版本不对应； |
| **PALYM4_INIT_DECODER_ERROR** | 19 | 初始化解码器失败； |
| **PLAYM4_CHECK_FILE_ERROR** | 20 | 文件太短或码流无法识别； |
| **PLAYM4_INIT_TIMER_ERROR** | 21 | 初始化多媒体时钟失败； |
| **PLAYM4_BLT_ERROR** | 22 | 位拷贝失败； |
| **PLAYM4_UPDATE_ERROR** | 23 | 显示overlay失败； |
| **PLAYM4_OPEN_FILE_ERROR_MULTI** | 24 | 打开文件失败，流类型是复合流； |
| **PLAYM4_OPEN_FILE_ERROR_VIDEO** | 25 | 打开文件失败，流类型是视频流； |
| **PLAYM4_JPEG_COMPRESS_ERROR** | 26 | JPEG压缩失败； |
| **PLAYM4_EXTRACT_NOT_SUPPORT** | 27 | 文件不支持； |
| **PLAYM4_EXTRACT_DATA_ERROR** | 28 | 数据错误； |
| **PLAYM4_SECRET_KEY_ERROR** | 29 | 解码密钥错误； |
| **PLAYM4_DECODE_KEYFRAME_ERROR** | 30 | 解码关键帧失败； |
| **PLAYM4_NEED_MORE_DATA** | 31 | 数据不足； |
| **PLAYM4_INVALID_PORT** | 32 | 无效端口号； |
| **PLAYM4_NOT_FIND** | 33 | 查找失败； |
| **PLAYM4_NEED_LARGER_BUFFER** | 34 | 需要更大的缓冲区； |
| **PLAYM4_FAIL_UNKNOWN** | 99 | 未知的错误； |

鱼眼部分错误码：

| **错误类型** | 错误值 | 错误信息 |
| --- | --- | --- |
| **PLAYM4_FEC_ERR_ENABLEFAIL** | 100 | 鱼眼模块加载失败; |
| **PLAYM4_FEC_ERR_NOTENABLE** | 101 | 鱼眼模块没有加载; |
| **PLAYM4_FEC_ERR_NOSUBPORT** | 102 | 子端口没有分配; |
| **PLAYM4_FEC_ERR_PARAMNOTINIT** | 103 | 没有初始化对应端口的参数; |
| **PLAYM4_FEC_ERR_SUBPORTOVER** | 104 | 子端口已经用完; |
| **PLAYM4_FEC_ERR_EFFECTNOTSUPPORT** | 105 | 该安装方式下这种效果不支持; |
| **PLAYM4_FEC_ERR_INVALIDWND** | 106 | 非法的窗口; |
| **PLAYM4_FEC_ERR_PTZOVERFLOW** | 107 | PTZ位置越界; |
| **PLAYM4_FEC_ERR_RADIUSINVALID** | 108 | 圆心参数非法; |
| **PLAYM4_FEC_ERR_UPDATENOTSUPPORT** | 109 | 指定的安装方式和矫正效果，该参数更新不支持; |
| **PLAYM4_FEC_ERR_NOPLAYPORT** | 110 | 播放库端口没有启用; |
| **PLAYM4_FEC_ERR_PARAMVALID** | 111 | 参数为空; |
| **PLAYM4_FEC_ERR_INVALIDPORT** | 112 | 非法子窗口; |
| **PLAYM4_FEC_ERR_PTZZOOMOVER** | 113 | PTZ矫正范围越界; |
| **PLAYM4_FEC_ERR_OVERMAXPORT** | 114 | 矫正通道饱和，最大支持的矫正通道为四个; |
| **PLAYM4_FEC_ERR_ENABLED** | 115 | 该端口已经启用了鱼眼模块; |
| **PLAYM4_FEC_ERR_D3DACCENOTENABLE** | 116 | D3D加速没有开启; |
| **PLAYM4_FEC_ERR_PLACETYPE** | 117 | 安装方式不对.一个播放库port，对应一种安装方式; |
| **PLAYM4_FEC_ERR_NULLWND** | 118 | 设置的鱼眼窗口hWnd为null或者鱼眼port的窗口更换; |
| **PLAYM4_FEC_ERR_CorrectType** | 119 | 矫正方式错误; |

#### Return Values

错误码，详见错误码宏定义。

---

<a id="sec_022"></a>
#### PlayM4_GetPort

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_GetPort

获取未使用的通道号。

```
int  PlayM4_GetPort(
  int*    nPort
);
```

#### Parameters

*nPort*
:   [out] 播放通道号，指向用于获取端口号的LONG型变量指针

#### Return Values

成功返回1；失败返回0。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

获取未使用的通道号,通道号的上限为500。

做轮巡操作时，不建议不断进行PlayM4_GetPort和PlayM4_FreePort的操作。

#### See Also

**[PlayM4_FreePort](PlayM4_FreePort.html)**

---

<a id="sec_023"></a>
#### PlayM4_FreePort

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_FreePort

释放已使用的通道号。

```
int  PlayM4_FreePort(
  int      nPort
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

#### Return Values

成功返回1；失败返回0。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

释放已使用的通道号，释放成功后，最好将nPort置为-1。

做轮巡操作时，不建议不断进行PlayM4_GetPort和PlayM4_FreePort的操作。

#### See Also

**[PlayM4_GetPort](PlayM4_GetPort.html)**

---

<a id="sec_025"></a>
#### PlayM4_OpenFile

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_OpenFile

打开文件。

```
int  PlayM4_OpenFile(
  int      nPort,
  char*    sFileName
);
```

#### Parameters

*nPort*
:   [in]
    播放通道号

*sFileName*
:   [in]
    文件名

#### Return Values

1表示成功，0表示失败。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### See Also

**[PlayM4_CloseFile](PlayM4_CloseFile.html)  

---**

<a id="sec_026"></a>
#### PlayM4_CloseFile

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_CloseFile

关闭文件。

```
int  PlayM4_CloseFile(
  int    nPort
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

#### Return Values

成功返回1；失败返回0。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### See Also

**[PlayM4_OpenFile](PlayM4_OpenFile.html)  

---**

<a id="sec_028"></a>
#### PlayM4_SetStreamOpenMode

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_SetStreamOpenMode

设置流播放模式。

```
int  PlayM4_SetStreamOpenMode(
  int       nPort,
  unsigned int      nMode
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

*nMode*
:   [in] 流播放模式，如下所示：

| **宏定义** | 宏定义值 | 含义 |
| --- | --- | --- |
| **STREAME_REALTIME** | 0 | 此模式（默认）下, 会尽量保正实时性, 防止数据阻塞; 而且数据检查严格 |
| **STREAME_FILE** | 1 | 此模式下按时间戳播放 |

#### Return Values

成功返回1；失败返回0。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

必须在播放之前设置。2.2以上版本SDK以后可以做暂停，快放，慢放，单帧播放操作。PlayM4_SetStreamOpenMode在PlayM4_OpenStream之前调用才有效。

#### See Also

**[PlayM4_GetStreamOpenMode](PlayM4_GetStreamOpenMode.html)**

---

<a id="sec_029"></a>
#### PlayM4_GetStreamOpenMode

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_GetStreamOpenMode

获取流播放模式。

```
int  PlayM4_GetStreamOpenMode(
  int    nPort
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

#### Return Values

STREAME_REALTIME或STREAME_FILE。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### See Also

**[PlayM4_SetStreamOpenMode](PlayM4_SetStreamOpenMode.html)**

---

<a id="sec_030"></a>
#### PlayM4_OpenStream

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_OpenStream

打开流。

```
int  PlayM4_OpenStream(
  int               nPort,
  unsigned char*    pFileHeadBuf,
  unsigned int      nSize,
  unsigned int      nBufPoolSize
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

*pFileHeadBuf*
:   [in] 文件头数据

*nSize*
:   [in] 文件头长度

*nBufPoolSize*
:   [in] 设置播放器中存放数据流的缓冲区大小。范围是SOURCE_BUF_MIN~ SOURCE_BUF_MAX。该值过小会导致无法解码。

| **宏定义** | 宏定义值 | 含义 |
| --- | --- | --- |
| **SOURCE_BUF_MIN** | 1024*50 | 缓冲数据流缓冲最小值 |
| **SOURCE_BUF_MAX** | 1024*100000 | 缓冲数据流缓冲最大值 |

#### Return Values

1表示成功，0表示失败。

#### Remarks

当前播放库已经支持无头码流，文件头长度可以为零，若无头码流则码流必须为海康设备编码的码流，且建议从文件开头部分到能解析出正确的I帧，此时数据大小必须小于10K。

RTP封装没有海康头或者SDP信息，则无法支持打开流;

在无头情况下打开流，打开声音操作都会返回成功;

网络状况差，数据不均匀或者有丢弃会引起卡顿情况

#### Example

以流模式解码数据码流为例，本示例以本地录像文件test.mp4模拟的实时码流数据

```

CFile  m_TestFile;
int   nPort = -1;
void Start()
{
    //获得文件头长度；
    unsigned int nLength  =  PlayM4_GetFileHeadLength();
    unsigned char* pFileHead  =  new BYTE[nLength];

    //打开文件；
    m_TestFile.Open("test.mp4 ", CFile::modeRead,NULL);
    m_TestFile.Read(pFileHead,nLength);
    
    //获取播放通道号
    PlayM4_GetPort(&nPort);
	
    //设置模式
    PlayM4_SetStreamOpenMode(nPort,STREAME_FILE);

    //打开流接口
    If (!PlayM4_OpenStream(nPort,pFileHead, nLength,1024*1000))
    {
      m_strPlayFileName="";
      MessageBox("文件打不开");
     }

    //读取数据送入播放库解码
     InputData();
		
    //开始解码，若需要显示视频图像则送入正确的窗口句柄；若只需要解码不需要显示，则可以将窗口句柄设置为NULL，即PlayM4_Play( nPort, NULL))
     m_bPlaying  =  PlayM4_Play( nPort, m_hWnd);
     delete []pFileHead;

     //播放完成后，回收播放资源
     //停止解码
      PlayM4_Stop(nPort);
     //关闭数据流
      PlayM4_CloseStream(nPort);
     //释放播放通道号
      PlayM4_FreePort(nPort);
      nPort = -1;
}	
		
///////////////////////////////////////////////////////////////////////////////
void InputData()
{
    unsigned char pBuf[4096];
    unsigned int  dwError = 0;

    while (1)
    {
        if(!(m_TestFile.Read(pBuf,sizeof(pBuf)))
        {
                //File end;
	        return;
         }
```

```

          while (!PlayM4_InputData(nPort,pBuf,sizeof(pBuf)))
         {
```

```

                if(!m_bPlaying)
	         return;//如果已经停止播放，则退出；

           dwError = PlayM4_GetLastError(nPort);
           if (dwError == 11)//缓冲区满，输入流失败，需要重复送入数据
           {
               sleep(2);
               continue;
            }
         }
    }

}


```

#### See Also

**[PlayM4_CloseStream](PlayM4_CloseStream.html)**

---

<a id="sec_031"></a>
#### PlayM4_CloseStream

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_CloseStream

关闭流。

```
int PlayM4_CloseStream(
  int  nPort
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

#### Return Values

成功返回1；失败返回0。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### See Also

**[PlayM4_OpenStream](PlayM4_OpenStream.html)**

---

<a id="sec_032"></a>
#### PlayM4_InputData

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_InputData

输入流数据。

```
int PlayM4_InputData(
  int               nPort,
  unsigned char*    pBuf,
  unsigned int      nSize
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

*pBuf*
:   [in] 流数据缓冲区地址

*nSize*
:   [in] 流数据缓冲区大小

#### Return Values

1表示已经输入数据。0表示失败，数据没有输入成功。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

输入流数据，需要在开启流之后才能输入数据，返回0一般是由于内部缓冲区满。

我们建议：

1.在实时流情况下，因数据满而无法送入播放库，可以选择丢弃，后果是画面可能跳帧或者花屏，如果无法接受，则sleep几毫秒后，再尝试多送几次；

2.文件流回放模式下，数据满而导致无法送入播放库，需要不断尝试，直到PlayM4_InputData返回成功为止。

若PlayM4_InputData的数据是40字节头时，播放库内部会重新PlayM4_CloseStream然后再PlayM4_OpenStream，即关闭当前码流，重新开始新的码流。

#### See Also

**[PlayM4_SetStreamOpenMode](PlayM4_SetStreamOpenMode.html)   [PlayM4_OpenStream](PlayM4_OpenStream.html)

**[PlayM4_CloseStream](PlayM4_CloseStream.html)  

---****

<a id="sec_033"></a>
#### PlayM4_OpenStreamAdvanced

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_OpenStreamAdvanced

打开流（以协议的方式）。

```
int PlayM4_OpenStreamAdvanced(
  int                    nPort,
  int                    nProtocolType,
  PLAYM4_SESSION_INFO    pstSessionInfo,
  unsigned int           nBufPoolSize
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

*nProtocolType*
:   [in] 协议类型，目前仅支持RTSP协议

| **nProtocolType** | 宏定义值 | 含义 |
| --- | --- | --- |
| **PLAYM4_PROTOCOL_RTSP** | 1 | RTSP协议 |

*pstSessionInfo*
:   [in] 协议信息结构体，若取值为PLAYM4_SESSION_INFO_SDP，表示nSessionInfoTypeSDP信息

*nBufPoolSize*
:   [in] 协议数据大小

#### Return Values

1表示成功，0表示失败。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

该接口是使用非私有40个字节开流，现支持用SDP开流。SDP开流暂不支持G711、G722、G726、PCM音频。

当前只支持RTSP协议取流。

文件方式播放下，不能调用PlayM4_CloseStream；流播放下，不能调用PlayM4_CloseFile接口。流开关接口和文件开关接口不能交叉使用。

#### See Also

**[PlayM4_SetStreamOpenMode](PlayM4_SetStreamOpenMode.html)   [PlayM4_OpenStream](PlayM4_OpenStream.html)   [PlayM4_CloseStream](PlayM4_CloseStream.html)  
  

---**

<a id="sec_035"></a>
#### PlayM4_Play

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_Play

开启播放。

```
int PlayM4_Play(
  int   nPort,
  PLAYM4_HWND   hWnd
);
```

#### Parameters

*nPort*
:   [in]
    播放通道号

*HWND*
:   [in]
    播放视频的窗口句柄

#### Return Values

1表示成功，0表示失败。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

播放开始，播放视频画面大小将根据hWnd窗口调整，要全屏显示，只要把hWnd窗口放大到全屏。

开始解码线程，若送入的显示窗口句柄为NULL，则不显示，但是不影响解码。

#### See Also

**[PlayM4_Stop](PlayM4_Stop.html)   [PlayM4_Pause](PlayM4_Pause.html)  

**[PlayM4_Fast](PlayM4_Fast.html)   [PlayM4_Slow](PlayM4_Slow.html)  

---****

<a id="sec_036"></a>
#### PlayM4_Stop

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_Stop

关闭播放。

```
int PlayM4_Stop(
  int    nPort
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

#### Return Values

成功返回1；失败返回0。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### See Also

**[PlayM4_Play](PlayM4_Play.html)   [PlayM4_Pause](PlayM4_Pause.html)  

**[PlayM4_Fast](PlayM4_Fast.html)   [PlayM4_Slow](PlayM4_Slow.html)  

---****

<a id="sec_037"></a>
#### PlayM4_Pause

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_Pause

暂停/恢复播放。

```
int PlayM4_Pause(
  int             nPort,
  unsigned int    nPause
);
```

#### Parameters

*nPort*
:   [in]
    播放通道号

*nPause*
:   [in]
    1：暂停，0：恢复

#### Return Values

1表示成功，0表示失败。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### See Also

**[PlayM4_Play](PlayM4_Play.html)   [PlayM4_Pause](PlayM4_Stop.html)  

**[PlayM4_Fast](PlayM4_Fast.html)   [PlayM4_Slow](PlayM4_Slow.html)  

---****

<a id="sec_038"></a>
#### PlayM4_Slow

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_Slow

慢速播放。

```
int PlayM4_Slow(
  int    nPort
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

#### Return Values

1表示成功，0表示失败。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

每次调用将使当前播放速度慢一倍；最多调用4次；要恢复正常播放调用PlayM4_Play()，从当前位置开始正常播放。

不支持实时流慢放。

#### See Also

**[PlayM4_Play](PlayM4_Play.html)   [PlayM4_Stop](PlayM4_Stop.html)

**[PlayM4_Pause](PlayM4_Pause.html)   [PlayM4_Fast](PlayM4_Fast.html)

---****

<a id="sec_039"></a>
#### PlayM4_Fast

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_Fast

快速播放。

```
int PlayM4_Fast(
  int   nPort
);
```

#### Parameters

*nPort*
:   [in]
    播放通道号

#### Return Values

1表示成功，0表示失败。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

每次调用将使当前播放速度加快一倍，正常速度调用此接口最多调用4次；要恢复正常播放调用PlayM4_Play(),从当前位置开始正常播放；高清码流在高倍速播放时，由于受到解码和显示的限制，可能达不到所设置的速度。

最大播放速度跟码流和电脑CPU性能有很大关系，在CPU处于90%以上，或者一个核满的情况下，播放速度可能上不去，这属于硬件解码性能不足导致。

不支持实时流快放。

#### See Also

**[PlayM4_Play](PlayM4_Play.html)   [PlayM4_Stop](PlayM4_Stop.html)

**[PlayM4_Pause](PlayM4_Pause.html)   [PlayM4_Stop](PlayM4_Stop.html)

---****

<a id="sec_040"></a>
#### PlayM4_OneByOne

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_OneByOne

单帧前进。

```
int PlayM4_OneByOne(
  int   nPort
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

#### Return Values

1表示成功，0表示失败。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

恢复正常播放需要调用PlayM4_Play()。

实时流模式下不支持单帧步进。

正放到最后一帧或者倒放到起始帧，文件流模式下未及时送数据，导致下一帧没上来会导致错误。

若设置丢B帧，只解I帧情况下，单帧不一定是和之前帧连续的，此时跳帧是合理的。

若码流错误情况下，也可导致跳帧的情况。

#### See Also

**[PlayM4_OneByOneBack](PlayM4_OneByOneBack.html)   [PlayM4_Play](PlayM4_Play.html)

---**

<a id="sec_041"></a>
#### PlayM4_OneByOneBack

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_OneByOneBack

单帧回退。

```
int PlayM4_OneByOneBack(
  int   nPort
);
```

#### Parameters

*nPort*
:   [in]
    播放通道号

#### Return Values

1表示成功，0表示失败。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

- 每调用一次倒退一帧。倒放到最后一帧或者正放到第一帧时，返回失败。
- 单帧回退功能，只支持文件播放模式，而且必须在文件索引生成之后才能调用。流模式播放时，实时流模式(STREAME_REALTIME)下不支持，文件流模式(STREAME_FILE)可支持单帧后退，但是需要应用层将单帧后退目标帧所在的GOP送入到播放库中去解码。单帧回退暂不支持TS封装文件。
- 在设置丢B帧情况下，单帧不一定和之前的帧连续，此时跳帧是合理的。
- 由于同步机制影响，单帧后退时，智能信息显示与正放时有所不同。

#### See Also

**[PlayM4_OneByOne](PlayM4_OneByOne.html)   [PlayM4_Play](PlayM4_Play.html)

---**

<a id="sec_042"></a>
#### PlayM4_PlaySound

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_PlaySound

以独占方式打开声音。

```
int PlayM4_PlaySound(
  int    nPort
);
```

#### Parameters

*nPort*
:   [in]
    播放通道号

#### Return Values

1表示成功，0表示失败。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

- 该接口是以独占的式打开声音，即同一时刻只能有一路声音。如果现在已经有声音打开，则自动关闭原来已经打开的声音，默认情况下声音是关闭的。
- PlayM4_PlaySoundShare、PlayM4_StopSoundShare是以共享的方式打开声音。PlayM4_PlaySound、PlayM4_StopSound、PlayM4_PlaySoundShare、PlayM4_StopSoundShare需要配对调用。在播放声音过程中，建议PlayM4_PlaySound、PlayM4_PlaySoundShare不要混用。
- 如果PlayM4_OpenStream的时候40字节海康头未申明编码类型，PlayM4_PlaySound会报错
- 播放低帧率文件时，必须先开启声音再播放。

#### See Also

**[PlayM4_StopSound](PlayM4_StopSound.html)  [PlayM4_PlaySoundShare](PlayM4_PlaySoundShare.html)  [PlayM4_StopSoundShare](PlayM4_StopSoundShare.html)**

---

<a id="sec_043"></a>
#### PlayM4_StopSound

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_StopSound

关闭声音（独占方式）。

```
int PlayM4_StopSound(
);
```

#### Parameters

*无*

#### Return Values

成功返回1；失败返回0。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

同一时刻只能有一路声音。如果现在已经有声音打开，则自动关闭原来已经打开的声音,默认情况下声音是关闭的。

PlayM4_PlaySound、PlayM4_PlaySoundShare、PlayM4_StopSound、PlayM4_StopSoundShare需要配对调用；

在播放声音过程中，建议PlayM4_PlaySound，PlayM4_PlaySoundShare不要混用。

#### See Also

**[PlayM4_PlaySound](PlayM4_PlaySound.html)  [PlayM4_PlaySoundShare](PlayM4_PlaySoundShare.html)  [PlayM4_StopSoundShare](PlayM4_StopSoundShare.html)**

---

<a id="sec_044"></a>
#### PlayM4_PlaySoundShare

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_PlaySoundShare

以共享方式打开声音。

```
int PlayM4_PlaySoundShare(
  int    nPort
);
```

#### Parameters

*nPort*
:   [in]
    播放通道号

#### Return Values

1表示成功，0表示失败。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

- 该接口是以共享方式打开声音。而Playm4_PlaySound和PlayM4_StopSound是以独占方式播放声音的。
- PlayM4_PlaySoundShare，PlayM4_StopSoundShare需要配对调用；在播放声音过程中，建议PlayM4_PlaySound，PlayM4_PlaySoundShare不要混用。
- 如果PlayM4_OpenStream的时候40字节海康头未申明编码类型，PlayM4_PlaySoundShare会报错。
- 播放低帧率文件时，必须先开启声音再播放。

#### See Also

**[PlayM4_PlaySound](PlayM4_PlaySound.html)  [PlayM4_StopSound](PlayM4_StopSound.html)  [PlayM4_StopSoundShare](PlayM4_StopSoundShare.html)**

---

<a id="sec_045"></a>
#### PlayM4_StopSoundShare

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_StopSoundShare

关闭声音（共享方式）。

```
int PlayM4_StopSoundShare(
  int    nPort
);
```

#### Parameters

*nPort*
:   [in]
    播放通道号

#### Return Values

1表示成功，0表示失败。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

以共享方式关闭声音。Playm4_PlaySound和PlayM4_StopSound是以独占方式播放声音的。

PlayM4_PlaySoundShare，PlayM4_StopSoundShare需要配对调用；在播放声音过程中，建议PlayM4_PlaySound，PlayM4_PlaySoundShare不要混用。

#### See Also

**[PlayM4_PlaySound](PlayM4_PlaySound.html)  [PlayM4_StopSound](PlayM4_StopSound.html)  [PlayM4_PlaySoundShare](PlayM4_PlaySoundShare.html)**

---

<a id="sec_046"></a>
#### PlayM4_SetVolume

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_SetVolume

设置音量。

```
int PlayM4_SetVolume(
  int               nPort,
  unsigned short    nVolume
);
```

#### Parameters

*nPort*
:   [in]
    播放通道号

*nVolume*
:   [in]
    音量值，范围0-0XFFFF

#### Return Values

成功返回1；失败返回0。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

需要在play之后调用，play之前调用会报错，开启声音成功一次及创建声卡资源后才能去设置和获取音量。这里的音量是指声卡输出的主音量，会影响到其他的声音应用。

#### See Also

**[PlayM4_GetVolume](PlayM4_GetVolume.html)   [PlayM4_AdjustWaveAudio](PlayM4_AdjustWaveAudio.html)  

**[PlayM4_PlaySound](PlayM4_PlaySound.html)   [PlayM4_StopSound](PlayM4_StopSound.html)

**[PlayM4_PlaySoundShare](PlayM4_PlaySoundShare.html)   [PlayM4_StopSoundShare](PlayM4_StopSoundShare.html)

---******

<a id="sec_047"></a>
#### PlayM4_GetVolume

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_GetVolume

获取音量。

```
unsigned short PlayM4_GetVolume(
  int    nPort
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

#### Return Values

音量值。这里的音量是指声卡输出的主音量，会影响到其他的声音应用。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

需要在play之后调用，play之前调用会报错，开启声音成功一次及创建声卡资源后才能去设置和获取音量。

#### See Also

**[PlayM4_SetVolume](PlayM4_SetVolume.html)   [PlayM4_AdjustWaveAudio](PlayM4_AdjustWaveAudio.html)  

**[PlayM4_PlaySound](PlayM4_PlaySound.html)   [PlayM4_StopSound](PlayM4_StopSound.html)

**[PlayM4_PlaySoundShare](PlayM4_PlaySoundShare.html)   [PlayM4_StopSoundShare](PlayM4_StopSoundShare.html)

---******

<a id="sec_048"></a>
#### PlayM4_AdjustWaveAudio

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_AdjustWaveAudio*

调整WAVE波形。

```
int PlayM4_AdjustWaveAudio(
  int  nPort,
  int  nCoefficient
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

*nCoefficient*
:   [in] 调整参数，0是不调整，范围从MIN_WAVE_COEF 到 MAX_WAVE_COEF。若设定为MIN_WAVE_COEF表示音量最低，若设定为MAX_WAVE_COEF表示音量最大。

| **宏定义** | 宏定义值 | 含义 |
| --- | --- | --- |
| **MIN_WAVE_COEF** | -100 | 音频最小值; |
| **MAX_WAVE_COEF** | 100 | 音量最大值; |

#### Return Values

成功返回1；失败返回0。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

- 调整WAVE波形，可以改变声音的大小。该接口和PlayM4_SetVolume的不同在于，它是调整声音数据，只对指定这一路起作用，而PlayM4_SetVolume是调整声卡音量，对整个系统起作用。
- 注意：用这个函数会破坏音质，除非想每路单独调整音量，否则请谨慎使用。
- 当前版本的Linux和Mac系统的播放库暂不支持该接口。

#### See Also

**[PlayM4_SetVolume](PlayM4_SetVolume.html)   [PlayM4_GetVolume](PlayM4_GetVolume.html)

**[PlayM4_PlaySound](PlayM4_PlaySound.html)   [PlayM4_StopSound](PlayM4_StopSound.html)

**[PlayM4_PlaySoundShare](PlayM4_PlaySoundShare.html)   [PlayM4_StopSoundShare](PlayM4_StopSoundShare.html)

---******

<a id="sec_049"></a>
#### PlayM4_SetColor

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_SetColor

设置视频参数。

```
int PlayM4_SetColor(
  int             nPort,
  unsigned int    nRegionNum,
  int             nBrightness,
  int             nContrast,
  int             nSaturation,
  int             nHue
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

*nRegionNum*
:   [in] 显示区域，参考**[PlayM4_SetDisplayRegion](#sec_085)**；如果只有一个显示区域(通常情况)设为0

*nBrightness*
:   [in] 亮度 ，默认64； 范围0-128

*nContrast*
:   [in] 对比度，默认64； 范围0-128

*nSaturation*
:   [in] 饱和度，默认64； 范围0-128

*nHue*
:   [in] 色调 ，默认64； 范围0-128

#### Return Values

1表示成功，0表示失败。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

如果全部为默认值将不进行颜色调节。

当前版本暂不支持此接口

#### See Also

**[PlayM4_GetColor](PlayM4_GetColor.html)   [PlayM4_SetImageSharpen](PlayM4_SetImageSharpen.html)

---**

<a id="sec_050"></a>
#### PlayM4_GetColor

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_GetColor

获取视频参数。

```
int PlayM4_GetColor(
  int             nPort,
  unsigned int    nRegionNum,
  int            *pBrightness,
  int            *pContrast,
  int            *pSaturation,
  int            *pHue
);
```

#### Parameters

*nPort*
:   [in] 播放库端口号

*nRegionNum*
:   [in] 显示区域

*pBrightness*
:   [out] 亮度 ，默认64； 范围0-128

*pContrast*
:   [out] 对比度，默认64； 范围0-128

*pSaturation*
:   [out] 饱和度，默认64； 范围0-128

*pHue*
:   [out] 色调 ，默认64； 范围0-128

#### Return Values

成功返回1；失败返回0。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

当前版本暂不支持此接口

#### See Also

**[PlayM4_SetColor](PlayM4_SetColor.html)   [PlayM4_SetImageSharpen](PlayM4_SetImageSharpen.html)  

---**

<a id="sec_051"></a>
#### PlayM4_SetImageSharpen

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_SetImageSharpen

设置图像锐化。

```
int PlayM4_SetImageSharpen(
  int             nPort,
  unsigned int    nLevel
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

*nLevel*
:   [in] 锐化级别（1～6，0不做锐化，1低级，6高级）默认不做锐化

#### Return Values

成功返回1；失败返回0。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

当前版本暂不支持此接口

#### See Also

**[PlayM4_SetColor](PlayM4_SetColor.html)   [PlayM4_GetColor](PlayM4_GetColor.html)  

---**

<a id="sec_052"></a>
#### PlayM4_SetRotateAngle

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_SetRotateAngle

设置图像旋转模式。

```
int PlayM4_SetRotateAngle(
  int     nPort,
  unsigned int    nRegionNum,
  unsigned int    dwType
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

*nRegionNum*
:   [in] 显示区域号

*dwType*
:   [in] 详见“Remarks”说明

#### Remarks

鱼眼窗口不会随播放窗口旋转。

不同的dwType值对应不同的宏定义值和旋转模式，如下表所示：

| dwType值 | 宏定义值 | 对应旋转模式 |
| --- | --- | --- |
| **R_ANGLE_0** | -1 | 不旋转 |
| **R_ANGLE_L90** | 0 | 向左旋转90度 |
| **R_ANGLE_R90** | 1 | 向右旋转90度 |
| **R_ANGLE_180** | 2 | 旋转180度 |

#### Return Values

成功返回1；失败返回0。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

POS信息、热成像信息、部分温度信息（点和框支持），此外温度信息中的字符信息不支持旋转。

#### See Also

**[PlayM4_SetColor](PlayM4_SetColor.html)   [PlayM4_GetColor](PlayM4_GetColor.html)  

**[PlayM4_SetImageSharpen](PlayM4_SetImageSharpen.html)

**[PlayM4_Play](PlayM4_Play.html)   [PlayM4_Stop](PlayM4_Stop.html)  

---******

<a id="sec_053"></a>
#### PlayM4_GetCurrentFrameRate

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_GetCurrentFrameRate

获取当前帧率。

```
unsigned int PlayM4_GetCurrentFrameRate(
  int     nPort
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

#### Return Values

成功返回当前码流中当前编码帧率；失败返回0xffffffff。获取错误码调用[PlayM4_GetLastError](#sec_020)。

#### Remarks

如果码流中的帧率小于1，则返回0。在未调用PlayM4_Play接口时调用此接口则接口返回值无实际参考意义。

#### See Also

**[PlayM4_Play](PlayM4_Play.html)   [PlayM4_Stop](PlayM4_Stop.html)  

---**

<a id="sec_054"></a>
#### PlayM4_GetFileHeadLength

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_GetFileHeadLength

获取文件头长度。

```
unsigned int PlayM4_GetFileHeadLength(
);
```

#### Parameters

*无*

#### Return Values

返回用于交互的海康媒体文件头或海康媒体信息头的大小，得到当前版本播放器能播放的文件的文件头长度。 主要应用在流播放器的
STREAME_FILE模式下。以便读出文件头作为PlayM4_OpenStream()的输入参数。

获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### See Also

**[PlayM4_SetStreamOpenMode](PlayM4_SetStreamOpenMode.html)   [PlayM4_GetStreamOpenMode](PlayM4_GetStreamOpenMode.html)  

**[PlayM4_OpenStream](PlayM4_OpenStream.html)   [PlayM4_CloseStream](PlayM4_CloseStream.html)  

**[PlayM4_Play](PlayM4_Play.html)   [PlayM4_Stop](PlayM4_Stop.html)  

---******

<a id="sec_055"></a>
#### PlayM4_GetFileTime

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_GetFileTime

获取文件总时间。

```
unsigned int PlayM4_GetFileTime(
  int     nPort
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

#### Return Values

文件总时间长度，单位秒；若失败返回0xffffffff。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

不支持对正在写入的文件进行时间的读取。在未调用PlayM4_Play接口时调用此接口则接口返回值无实际参考意义。

此接口只是用于文件模式下调用。

#### See Also

**[PlayM4_OpenFile](PlayM4_OpenFile.html)   [PlayM4_CloseFile](PlayM4_CloseFile.html)

**[PlayM4_Play](PlayM4_Play.html)   [PlayM4_Stop](PlayM4_Stop.html)  

**[PlayM4_GetFileTotalFrames](PlayM4_GetFileTotalFrames.html)  

---******

<a id="sec_056"></a>
#### PlayM4_GetFileTotalFrames

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_GetFileTotalFrames

获取文件总帧数。

```
unsigned int PlayM4_GetFileTotalFrames(
  int     nPort
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

#### Return Values

成功返回文件总帧数；失败返回0xffffffff，获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

不支持对正在写入的文件进行帧数的读取。
在未调用PlayM4_Play接口时调用此接口则接口返回值无实际参考意义。

此接口只是用于文件模式下调用。

#### See Also

**[PlayM4_Play](PlayM4_Play.html)   [PlayM4_Stop](PlayM4_Stop.html)  

**[PlayM4_GetFileTime](PlayM4_GetFileTime.html)  

---****

<a id="sec_057"></a>
#### PlayM4_GetPictureSize

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_GetPictureSize

获取原始图像大小。

```
int PlayM4_GetPictureSize(
  int     nPort,
  int    *pWidth,
  int    *pHeight
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

*pWidth*
:   [out] 原始图像的宽度

*pHeight*
:   [out] 原始图像的高度

#### Return Values

成功返回1；失败返回0。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

获得码流中原始图像的大小，根据此大小来设置显示窗口的区域，可以不使用显卡做缩放工作，对于那些不支持硬件缩放的显卡来说非常有用。
该函数获取的是刚刚播放那帧数据的长宽，因此只有当播放开始后才能获取准确的值。

建议配合PlayM4_SetEncTypeChangeCallBack使用。
在未调用PlayM4_Play接口时调用此接口则接口返回值无实际参考意义。

#### See Also

**[PlayM4_OpenFile](PlayM4_OpenFile.html)   [PlayM4_CloseFile](PlayM4_CloseFile.html)

**[PlayM4_Play](PlayM4_Play.html)   [PlayM4_Stop](PlayM4_Stop.html)  

---****

<a id="sec_058"></a>
#### PlayM4_GetPlayedFrames

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_GetPlayedFrames

获取已解码的视频帧数。

```
unsigned int PlayM4_GetPlayedFrames(
  int    nPort
);
```

#### Parameters

*nPort*
:   [in]
    播放通道号

#### Return Values

成功返回已经解码的视频帧数；失败返回0xffffffff。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

在未调用PlayM4_Play接口时调用此接口则接口返回值无实际参考意义。

#### See Also

**[PlayM4_OpenFile](PlayM4_OpenFile.html)   [PlayM4_CloseFile](PlayM4_CloseFile.html)

**[PlayM4_Play](PlayM4_Play.html)   [PlayM4_Stop](PlayM4_Stop.html)  

---****

<a id="sec_059"></a>
#### PlayM4_GetPlayedTime

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_GetPlayedTime

获取已播放时间。

```
unsigned int PlayM4_GetPlayedTime(
  int    nPort
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

#### Return Values

成功返回文件当前播放时间，单位秒；失败返回0xffffffff。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

在未调用PlayM4_Play接口时调用此接口则接口返回值无实际参考意义。

#### See Also

**[PlayM4_OpenFile](PlayM4_OpenFile.html)   [PlayM4_CloseFile](PlayM4_CloseFile.html)

**[PlayM4_Play](PlayM4_Play.html)   [PlayM4_Stop](PlayM4_Stop.html)  

---****

<a id="sec_060"></a>
#### PlayM4_GetSpecialData

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_GetSpecialData

获取当前显示帧的全局时间。

```
unsigned int PlayM4_GetSpecialData(
  int     nPort
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

#### Return Values

失败返回0xffffffff，成功则返回一个全局时间的压缩值，精确到秒

**#define GET_YEAR(_time_) (((_time_)>>26) + 2000)**

**#define GET_MONTH(_time_) (((_time_)>>22) & 15)**

**#define GET_DAY(_time_) (((_time_)>>17) & 31)**

**#define GET_HOUR(_time_) (((_time_)>>12) & 31)**

**#define GET_MINUTE(_time_) (((_time_)>>6) & 63)**

**#define GET_SECOND(_time_) (((_time_)>>0) & 63)**

**获取错误码调用**[PlayM4_GetLastError](#sec_020)**。**

#### Remarks

有正常图像显示后才能调用此接口。

获取到的系统时间是在码流封装层里面的，可能与图像OSD上面有一定误差。

第三方码流或者未打系统时间的海康码流都无法获取到系统时间。

#### See Also

**[PlayM4_GetPort](PlayM4_GetPort.html)   [PlayM4_FreePort](PlayM4_FreePort.html)

**[PlayM4_OpenFile](PlayM4_OpenFile.html)   [PlayM4_CloseFile](PlayM4_CloseFile.html)

**[PlayM4_Play](PlayM4_Play.html)   [PlayM4_Stop](PlayM4_Stop.html)  

---******

<a id="sec_061"></a>
#### PlayM4_GetSystemTime

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_GetSystemTime

获取当前播放帧的全局时间。

```
int PlayM4_GetSystemTime(
  int                   nPort,
 PLAYM4_SYSTEM_TIME    *pstSystemTime
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

*pstSystemTime*
:   [out] 全局时间

#### Return Values

1表示成功，0表示失败。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

获取当前播放帧对应的全局时间。

#### See Also

**[PlayM4_SetFileRefCallBack](PlayM4_SetFileRefCallBack.html)  

**[PlayM4_ReversePlay](PlayM4_ReversePlay.html)  

---****

<a id="sec_063"></a>
#### PlayM4_GetPlayPos

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_GetPlayPos

获取文件当前播放位置（百分比）。

```
float PlayM4_GetPlayPos(
  int     nPort
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

#### Return Values

范围0-100%，获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

获得文件播放指针的相对位置在PlayM4_Play之后调用才有效。

非文件（实时流，文件流）模式下调用此接口，则返回失败

#### See Also

**[PlayM4_SetPlayPos](PlayM4_SetPlayPos.html)  

**[PlayM4_SetPlayedTimeEx](PlayM4_SetPlayedTimeEx.html)   [PlayM4_GetPlayedTimeEx](PlayM4_GetPlayedTimeEx.html)  

**[PlayM4_SetCurrentFrameNum](PlayM4_SetCurrentFrameNum.html)   [PlayM4_GetCurrentFrameNum](PlayM4_GetCurrentFrameNum.html)  

---******

<a id="sec_064"></a>
#### PlayM4_SetPlayPos

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_SetPlayPos

设置文件当前播放位置（百分比）。

```
int PlayM4_SetPlayPos(
  int      nPort,
  float    fRelativePos
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

*fRelativePos*
:   [in] 播放位置，范围0-100%

#### Return Values

1表示成功，0表示失败。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

设置文件播放指针的相对位置（百分比）。如果在建立文件索引的前提下使用, 为精确定位, 否则即为粗略定位，设置的定位位置后面如果没有I帧则定位操作实际无效果；在PlayM4_Play之后调用才有效。

若定位的有效位置下没有关键帧，则无法定位到数据。

非文件（实时流，文件流）模式下，定位则返回失败

#### See Also

**[PlayM4_GetPlayPos](PlayM4_GetPlayPos.html)  

**[PlayM4_SetPlayedTimeEx](PlayM4_SetPlayedTimeEx.html)   [PlayM4_GetPlayedTimeEx](PlayM4_GetPlayedTimeEx.html)  

**[PlayM4_SetCurrentFrameNum](PlayM4_SetCurrentFrameNum.html)   [PlayM4_GetCurrentFrameNum](PlayM4_GetCurrentFrameNum.html)  

---******

<a id="sec_065"></a>
#### PlayM4_SetPlayedTimeEx

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_SetPlayedTimeEx

设置文件当前播放时间（毫秒）。

```
int PlayM4_SetPlayedTimeEx(
  int             nPort,
  unsigned int    nTime
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

*nTime*
:   [in] 设置文件播放到指定时间，单位：毫秒  
    文件播放时，该参数是相对文件的第一个I帧的偏移时间；  
    流播放并且播放模式为STREAME_FILE时，该参数指相对于送入的第一个GOP起始I帧的相对时标

#### Return Values

成功返回1；失败返回0。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

PlayM4_OpenFile文件播放，需要在建立文件索引的前提下调用才能实现精确定位，否则为粗略定位；设置的定位位置后面如果没有I帧则定位操作实际无效果。

当播放模式为流模式即STREAME_REALTIME时，不支持调用该接口进行定位。

#### See Also

**[PlayM4_GetPlayedTimeEx](PlayM4_GetPlayedTimeEx.html)  

**[PlayM4_GetPlayPos](PlayM4_GetPlayPos.html)   [PlayM4_SetPlayPos](PlayM4_SetPlayPos.html)  

**[PlayM4_SetCurrentFrameNum](PlayM4_SetCurrentFrameNum.html)   [PlayM4_GetCurrentFrameNum](PlayM4_GetCurrentFrameNum.html)  

---******

<a id="sec_066"></a>
#### PlayM4_GetPlayedTimeEx

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_GetPlayedTimeEx

获取文件当前播放时间（毫秒）。

```
unsigned int  PlayM4_GetPlayedTimeEx(
  int     nPort
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

#### Return Values

文件当前播放的时间，单位毫秒,在PlayM4_Play之后调用才有效。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### See Also

**[PlayM4_SetPlayedTimeEx](PlayM4_SetPlayedTimeEx.html)  

**[PlayM4_GetPlayPos](PlayM4_GetPlayPos.html)   [PlayM4_SetPlayPos](PlayM4_SetPlayPos.html)  

**[PlayM4_SetCurrentFrameNum](PlayM4_SetCurrentFrameNum.html)   [PlayM4_GetCurrentFrameNum](PlayM4_GetCurrentFrameNum.html)  

---******

<a id="sec_067"></a>
#### PlayM4_SetCurrentFrameNum

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_SetCurrentFrameNum

设置文件当前播放帧号。

```
int PlayM4_SetCurrentFrameNum(
  int             nPort,
  unsigned int    nFrameNum
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

*nFrameNum*
:   [in] 帧号

#### Return Values

1表示成功，0表示失败。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

设置当前播放播放位置到指定帧号；根据帧号来定位播放位置。如果在建立文件索引的前提下使用, 为精确定位, 否则即为粗略定位，设置的定位位置后面如果没有I帧则定位操作实际无效果；在PlayM4_Play之后调用才有效。

#### See Also

**[PlayM4_GetCurrentFrameNum](PlayM4_GetCurrentFrameNum.html)  

**[PlayM4_SetPlayedTimeEx](PlayM4_SetPlayedTimeEx.html)   [PlayM4_GetPlayedTimeEx](PlayM4_GetPlayedTimeEx.html)

**[PlayM4_GetPlayPos](PlayM4_GetPlayPos.html)   [PlayM4_SetPlayPos](PlayM4_SetPlayPos.html)  

---******

<a id="sec_068"></a>
#### PlayM4_GetCurrentFrameNum

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_GetCurrentFrameNum

获取文件当前播放帧号。

```
unsigned int PlayM4_GetCurrentFrameNum(
  int     nPort
);
```

#### Parameters

*nPort*
:   [in] 播放库通道号

#### Return Values

当前播放的帧序号，获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

得到当前播放的帧序号。有在PlayM4_Play之后调用才有效。

未显示出图像前，获取到数值无效。

#### See Also

**[PlayM4_SetCurrentFrameNum](PlayM4_SetCurrentFrameNum.html)  

**[PlayM4_SetPlayedTimeEx](PlayM4_SetPlayedTimeEx.html)   [PlayM4_GetPlayedTimeEx](PlayM4_GetPlayedTimeEx.html)

**[PlayM4_GetPlayPos](PlayM4_GetPlayPos.html)   [PlayM4_SetPlayPos](PlayM4_SetPlayPos.html)  

---******

<a id="sec_069"></a>
#### PlayM4_GetMpOffset

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_GetMpOffset

Mp4(3gp)索引前置文件流式获取播放时间对应的文件偏移位置。

```
int PlayM4_GetMpOffset(
  int    nPort,
  int    nTime,
  int    *nOffset
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

*nTime*
:   [in] 播放相对时间

*nTime*
:   [Out] 文件偏移位置

#### Return Values

若成功返回1,失败返回0，获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

mp4封装由于没有hik头，如果要用hik头开流，则需要自己构造hik头；不能将mp4封装前面40字节索引信息用来开流，否则会导致文件缺少40字节信息而无法播放；

mp4封装文件前40字节无hik头时，也可以无头开流；

暂支持h264、h265编码的mp4封装索引前置流式播放；

定位送入数据不是给出的偏移位置数据，无法播放

#### See Also

**[PlayM4_SetSourceBufCallBack](PlayM4_SetSourceBufCallBack.html)   [PlayM4_ResetSourceBuffer](PlayM4_ResetSourceBuffer.html)

---**

<a id="sec_071"></a>
#### PlayM4_SetDecCBStream

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_SetDecCBStream

设置解码回调流类型。

```
int PlayM4_SetDecCBStream(
  int             nPort,
  unsigned int    nStream
);
```

#### Parameters

*nPort*
:   [in]
    播放通道号

*nStream*
:   [in]
    取值如下:

| **取值** | 含义 |
| --- | --- |
| **1** | 视频流; |
| **2** | 音频流; |
| **3** | 复合流; |

#### Return Values

成功返回1；失败返回0。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

建议在解码回调函数前使用。

#### See Also

**[PlayM4_SetDecCallBack](PlayM4_SetDecCallBack.html)   [PlayM4_SetDecCallBackMend](PlayM4_SetDecCallBackMend.html)  

**[PlayM4_SetDecCallBackExMend](PlayM4_SetDecCallBackExMend.html)   [PlayM4_SetDecodeFrameType](PlayM4_SetDecodeFrameType.html)  

---****

<a id="sec_072"></a>
#### PlayM4_SetDecodeFrameType

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_SetDecodeFrameType

设置视频帧解码类型。

```
int PlayM4_SetDecodeFrameType(
  int             nPort,
  unsigned int    nFrameType
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

*nFrameType*
:   [in] 解码帧类型说明，详见“Remarks”说明

#### Return Values

成功返回1；失败返回0。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

nFrameType解码帧类型说明，如下表所示：

| nFrameType宏定义 | nFrameType含义 | 宏定义值 |
| --- | --- | --- |
| **DECODE_NORMAIL** | 正常解码 | 0 |
| **DECODE_KEY_FRAME** | 只解关键帧 | 1 |
| **DECODE_NONE** | 不解视频帧 | 2 |
| **DECODE_SVC_HALF** | 解码svc码流1/2 | 3 |
| **DECODE_SVC_QUARTER** | 解码svc码流1/4 | 4 |
| **DECODE_SVC_EIGHTH** | 解码svc码流1/8 | 5 |
| **DECODE_ALL_FRAME** | 全解，分辨率大于等于1080P多倍速时不自动抽帧 | 6 |

设置为“不解视频帧”（DECODE_NONE）模式后将不支持定位、单帧前进、单帧后退功能。

#### See Also

**[PlayM4_SetDecCBStream](PlayM4_SetDecCBStream.html)**

**[PlayM4_SetDecCallBack](PlayM4_SetDecCallBack.html)   [PlayM4_SetDecCallBackMend](PlayM4_SetDecCallBackMend.html)**

**[PlayM4_SetDecCallBackExMend](PlayM4_SetDecCallBackExMend.html)**

---

<a id="sec_073"></a>
#### PlayM4_SetDecCallBackMend

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_SetDecCallBackMend

解码回调（增加用户传递参数）。

```
int PlayM4_SetDecCallBackMend(
  int         nPort,
  DecCBFun    fDecCBFun,
  int         nUser
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

*fDecCBFun*
:   [in] 解码回调函数，若不需要回调函数则置为NULL,否则不能为NULL

#### Callback Function

```
typedef void(CALLBACK *DecCBFun)(
  int           nPort,
  char         *pBuf,
  int           nSize,
 FRAME_INFO    *pFrameInfo,
  int           nUser,
  int           nReserved2
);
```

#### Callback Function Parameters

*nPort*
:   [out] 播放器通道号

*pBuf*
:   [out] 解码后的音视频数据指针

*nSize*
:   [out] 解码后的音视频数据pBuf的长度

*pFrameInfo*
:   [out] 图像和声音信息结构体指针

*nUser*
:   [out] 用户数据

*nReserved2*
:   [out] 保留参数

*nUser*
:   [in] 用户数据

#### Return Values

成功返回1；失败返回0。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

设置回调函数，替换播放器中的显示部分，由用户自己控制显示，该函数在PlayM4_Play之前调用，在PlayM4_Stop时自动失效，下次调用PlayM4_Play之前需要重新设置。

注意解码部分不控制速度，只要用户从回调函数中返回，解码器就会解码下一部分数据。

这个功能的使用需要用户对视频显示和声音播放有足够的了解，否则请慎重使用，有关知识请参阅directx开发包。

解码回调函数PlayM4_SetDecCallBack区别在于增加了用户传递参数，当前解码的视频数据格式为YV12，音频解码格式为PCM。

调用此回调函数后，则视频图像无显示。

#### See Also

**[PlayM4_SetDecCallBack](PlayM4_SetDecCallBack.html)   [PlayM4_SetDisplayCallBack](PlayM4_SetDisplayCallBack.html)  

**[PlayM4_SetDecCBStream](PlayM4_SetDecCBStream.html)   [PlayM4_SetDecodeFrameType](PlayM4_SetDecodeFrameType.html)  

**[PlayM4_SetDecCallBackExMend](PlayM4_SetDecCallBackExMend.html)  

---******

<a id="sec_074"></a>
#### PlayM4_SetDecCallBackExMend

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_SetDecCallBackExMend

解码回调（带目标数据和数据大小和用户指针）。

```
int PlayM4_SetDecCallBackExMend(
  int         nPort,
  DecCBFun    fDecCBFun,
  char*       pDest,
  int         nDestSize,
  int         nUser
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

*DecCBFun*
:   [in] 解码回调函数，若不需要回调函数则置为NULL，否则不能为NULL

#### Callback Function

```
typedef void(CALLBACK *DecCBFun)(
  int           nPort,
  char*         pBuf,
  int           nSize,
 FRAME_INFO    *pFrameInfo,
  int           nUser,
  int           nReserved2
);
```

#### Callback Function Parameters

*nPort*
:   [out] 播放器通道号

*pBuf*
:   [out] 解码后的音视频数据指针

*nSize*
:   [out] 解码后的音视频数据pBuf的长度

*pFrameInfo*
:   [out] 图像和声音信息结构体指针

*nUser*
:   [out] 用户数据

*nReserved2*
:   [out] 保留参数

*pDest*
:   [in] 目标数据，暂时设置为NULL

*nDestSize*
:   [in] 目标数据大小，暂时设置为0

*nUser*
:   [in] 用户指针

#### Return Values

成功返回1；失败返回0。。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

PlayM4_SetDecCallBackExMend与PlayM4_SetDecCallBackMend相比：

PlayM4_SetDecCallBackExMend会解码并显示，并将解码的数据以回调函数的方式给用户，但是PlayM4_SetDecCallBackMend仅仅将解码后的数据给用户，并不显示。

其中参数pDest和nDestSize没有具体的用处。可以置为NULL和0。

当前解码的视频数据格式为YV12，音频解码格式为PCM。

#### See Also

**[PlayM4_SetDecCBStream](PlayM4_SetDecCBStream.html)   [PlayM4_SetDecodeFrameType](PlayM4_SetDecodeFrameType.html)**

**[PlayM4_SetDisplayCallBack](PlayM4_SetDisplayCallBack.html)**

---

<a id="sec_075"></a>
#### PlayM4_SetFileEndCallback

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_SetFileEndCallback

文件结束回调。

```
int PlayM4_SetFileEndCallback(
  int                nPort,
  FileEndCallback    fFileEndCBFun,
  void              *pUser
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

*FileEndCallback*
:   [in] 文件结束回调函数

#### Callback Function

```
typedef void(FileEndCallback *fFileEndCBFun)(
  int      nPort,
  void    *pUser
);
```

#### Callback Function Parameters

*nPort*
:   [out] 播放器通道号

*pUser*
:   [out] 用户数据

*pUser*
:   [in]
    用户数据

#### Return Values

1表示成功，0表示失败。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

设置文件结束时要发送的消息；当文件播放完时，解码线程将不会自动结束，需要用户做停止工作设置文件播放结束回调函数。

在PlayM4_OpenSteam/PlayM4_OpenFile之前调用才有效。

回调与消息不能同时使用。

#### See Also

**[PlayM4_OpenFile](PlayM4_OpenFile.html)   [PlayM4_CloseFile](PlayM4_CloseFile.html)**

---

<a id="sec_076"></a>
#### PlayM4_SetEncTypeChangeCallBack

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_SetEncTypeChangeCallBack

设置变分辨率回调函数。

```
int PlayM4_SetEncTypeChangeCallBack(
  int          nPort,
  CALLBACK*    funEncChange,
  int          nUser
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

*funEncChange*
:   [in] 变分辨率回调函数

#### Callback Function

```
typedef void(CALLBACK *funEncChange)(
  int    nPort,
  int    nUser
);
```

#### Callback Function Parameters

*nPort*
:   [out] 播放通道号

*nUser*
:   [out] 用户数据

*nUser*
:   [in] 用户数据

#### Return Values

成功返回1；失败返回0。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

消息和回调函数不能同时使用。

#### See Also

**[PlayM4_Play](PlayM4_Play.html)   [PlayM4_Stop](PlayM4_Stop.html)  

---**

<a id="sec_077"></a>
#### PlayM4_ThrowBFrameNum

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_ThrowBFrameNum

设置丢B帧个数。

```
int  PlayM4_ThrowBFrameNum(
  int           nPort,
  unsigned int  nNum
);
```

#### Parameters

*nPort*
:   [in]
    播放通道号

*nNum*
:   [in]
    不解码B帧的帧数。范围0~2

#### Return Values

成功返回1；失败返回0。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

设置不解码B帧帧数，不解码B帧，可以减小CPU利用率，只支持pbb的这种带2个b帧的码流丢b帧处理；若编码类型中无B帧，则调用此接口无效。

如在快速播放，和支持多路而CPU利用率太高的情况下可以考虑使用。

---

<a id="sec_078"></a>
#### PlayM4_CheckDiscontinuousFrameNum

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_CheckDiscontinuousFrameNum*

检查帧号是否连续。

```
int PlayM4_CheckDiscontinuousFrameNum(
  int    nPort,
  int    bCheck
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

*bCheck*
:   [in] 是否设置检查帧号连续性。若为1：则检查帧号连续性。如果实际码流帧号不连续，会跳到下一个I帧；若为0：不检查帧号连续性。如果数据能解码，则播放，不直接跳至下一个I帧。

#### Return Values

成功返回1；失败返回0。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

检查帧号是否连续，在码流不连续的情况下，设置检查后，会跳下一个关键帧解码。

当前版本暂不支持此接口。

---

<a id="sec_079"></a>
#### PlayM4_SetCheckWatermarkCallBack

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_SetCheckWatermarkCallBack*

设置水印回调函数。

```
int PlayM4_SetCheckWatermarkCallBack(
  int                  nPort,
  funCheckWatermark    fCheckWatermarkFun,
   void*               nUser
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

*funCheckWatermark*
:   [in] 检查水印回调函数

#### Callback Function

```
typedef void(CALLBACK *funCheckWatermark)(
  int               nPort,
 WATERMARK_INFO*    pFrameInfo,
  void*             nUser
);
```

#### Callback Function Parameters

*nPort*
:   [out] 播放器通道号

*pWatermarkInfo*
:   [out] 水印信息结构体指针

*nUser*
:   [out] 用户数据

#### Return Values

1表示成功，0表示失败。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

一般只有海康私有封装和PS封装层有水印，其他没有水印。编码只支持标准264水印。

#### See Also

**[PlayM4_Play](PlayM4_Play.html)   [PlayM4_Stop](PlayM4_Stop.html)  

---**

<a id="sec_080"></a>
#### PlayM4_SetSecretKey

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_SetSecretKey

解码密钥。

```
int PlayM4_SetSecretKey(
  int      nPort,
  int      lKeyType,
  char    *pSecretKey,
  int      lKeyLen
);
```

#### Parameters

*nPort*
:   [in]
    播放通道号

*lKeyType*
:   [in]
    密钥类型（取值为0不加密；取值为1标识AES加密）

*pSecretKey*
:   [in]
    密钥串首地址

*lKeyLen*
:   [in]
    密钥长度，单位为bit（1字节为8 bit）

#### Return Values

成功返回1；失败返回0。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

如果在编码时设置了密钥，那么在解码之前需要调用该接口设置密钥才能正常解码。该接口在PlayM4_OpenStream/PlayM4_OpenFile之前调用才有效。检查参数lKeyType，现只支持AES机密方式，取值1，lKeyLen单位为bit，一般是16字节，128bit,若密钥长度不足128bit,则需要补0。因密钥信息无法从码流获取，因此该函数无法判断密钥内容是否正确。

#### See Also

**[PlayM4_OpenStream](PlayM4_OpenStream.html)   [PlayM4_OpenFile](PlayM4_OpenFile.html)  

**[PlayM4_SetEncryptTypeCallBack](PlayM4_SetEncryptTypeCallBack.html)  

---****

<a id="sec_081"></a>
#### PlayM4_SetEncryptTypeCallBack

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_SetEncryptTypeCallBack

加密码流回调函数。

```
int PlayM4_SetEncryptTypeCallBack(
  int             nPort,
  unsigned int    nType,
  CALLBACK*       EncryptTypeCBFun,
  int             nUser
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

*nType*
:   [in] nType=0表示码流加密标记位发生变化就回调，nType=1表示码流有加密位发生回调

*EncryptTypeCBFun*
:   [in] 加密码流回调函数

#### Callback Function

```
typedef void(CALLBACK *EncryptTypeCBFun)(
  int             nPort,
 ENCRYPT_INFO    *pEncryptInfo,
  int             nUser,
  int             nReserved2
);
```

#### Callback Function Parameters

*nPort*
:   [out] 播放通道号

*pEncryptInfo*
:   [out] 加密数据信息

*nUser*
:   [out] 用户数据

*nReserved2*
:   [out] 保留数据

*nUser*
:   [in] 用户数据

#### Return Values

成功返回1；失败返回0。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

仅仅支持加密码流，通过回调函数将加密的码流数据回调给用户。若无加密信息的码流调用此接口无效果。

#### See Also

**[PlayM4_SetSecretKey](PlayM4_SetSecretKey.html)  

---**

<a id="sec_082"></a>
#### PlayM4_SetDecodeThreadNum

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_SetDecodeThreadNum

设置解码线程，只针对H.264和H.265。

```
int PlayM4_SetDecodeThreadNum(
  int      nPort,
 unsigned  int      nThreads
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

*nThreads*
:   [in] 解码线程数

#### Return Values

成功返回1；失败返回0。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

设置软解码的解码线程个数：nThreads暂时对1、2、4、8、1000(复原标记值)有效(播放库内部默认有不同分辨率对应的解码线程个数),
8线程只有外面设置才会使用，因为消耗内存较多，库内默认不会使用8线程。

PlayM4_Play之后调用这个接口。

#### See Also

**[PlayM4_Play](PlayM4_Play.html)   [PlayM4_Stop](PlayM4_Stop.html)  

**[PlayM4_RenderPrivateData](PlayM4_RenderPrivateData.html)  

---****

<a id="sec_083"></a>
#### PlayM4_SetDecodeERC

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_SetDecodeERC

设置软解码Intra码流的差错隐藏等级。

```
BOOL PlayM4_SetDecodeERC(
  LONG             nPort,
  unsinged int           nLevel
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

*nLevel*
:   [in] 解码差错隐藏等级

#### Return Values

成功返回TRUE；失败返回FALSE。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

此接口只对H.264和H.265有效，PlayM4_GetPort之后调用。

Intra码流内部默认差错隐藏等级为1；用户可以不设置；

1-4的4个等级开启会增加解码内存（大概为1帧YUV的数据大小，即w*h/3/2），4等级开启会增加解码性能消耗。

Intra码流解码需要配合调用PlayM4_SkipErrorData接口使用，如PlayM4_SkipErrorData中bSkip设置为0，则解析不跳过冗余数据。

#### See Also

**[PlayM4_GetPort](PlayM4_GetPort.html)   [PlayM4_FreePort](PlayM4_FreePort.html)  

**[PlayM4_SetDecodeOrDisplayMode](PlayM4_SetDecodeOrDisplayMode.html)  

---****

<a id="sec_085"></a>
#### PlayM4_SetDisplayRegion

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_SetDisplayRegion

设置或增加显示区域。

```
int PlayM4_SetDisplayRegion(
  int            nPort,
  unsigned int   nRegionNum,
  HKRECT        *pSrcRect,
  PLAYM4_HWND    hDestWnd,
  int            bEnable
);
```

#### Parameters

*nPort*
:   [in]
    播放通道号

*nRegionNum*
:   [in]
    显示区域序号，0~(MAX_DISPLAY_WND-1)。如果nRegionNum为0，表示对主要显示窗口（PlayM4_Play中设置的窗口）进行设置，将忽略hDestWnd和bEnable的设置

*pSrcRect*
:   [in]
    设置在要显示的原始图像上的区域，如：如果原始图像是352*288，那么pSrcRect可设置的范围只能在（0，0，352，288）之中。如果pSrcRect=NULL,将显示整个图像

*hDestWnd*
:   [in]
    设置显示窗口。如果该区域的窗口已经设置过（打开过），那么该参数被忽略

*bEnable*
:   [in]
    打开（设置）或关闭显示区域

#### Return Values

1表示成功，0表示失败。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

设置或增加显示区域。可以做局部放大显示。

对于设置子窗口，HKRECT宽或者高小于16个像素点，不能做放大处理，显示原图像大小。

区域设置若超过图像原始大小，则以原始图像为限制，若超过图像大小，则不做放大处理

如果play之前调用电子放大接口，则接口对rect参数有效性无法做判断；因此该接口建议在正常播放状态下使用，未调用play之前设置的rect参数不做异常参数判断。

---

<a id="sec_086"></a>
#### PlayM4_SetDisplayRegionOnWnd

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_SetDisplayRegionOnWnd

设置多窗口分割显示区域。

```
int PlayM4_SetDisplayRegionOnWnd(
  int            nPort,
  unsigned int   nRegionNum,
  HKRECT        *pSrcRect,
  int            bEnable
);
```

#### Parameters

*nPort*
:   [in]
    播放通道号

*nRegionNum*
:   [in]
    显示区域序号，0~(MAX_DISPLAY_WND-1)。如果nRegionNum为0，表示对主要显示窗口（PlayM4_Play中设置的窗口）进行设置，将忽略hDestWnd和bEnable的设置

*pSrcRect*
:   [in]
    设置在要显示的原始图像上的区域，如：如果原始图像是352*288，那么pSrcRect可设置的范围只能在（0，0，352，288）之中。如果pSrcRect=NULL,将显示整个图像

*bEnable*
:   [in]
    打开（设置）或关闭显示区域

#### Return Values

1表示成功，0表示失败。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

设置多窗口分割显示区域。

---

<a id="sec_087"></a>
#### PlayM4_RefreshPlay

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_RefreshPlay

刷新显示。

```
int PlayM4_RefreshPlay(
  int     nPort
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

#### Return Values

1表示成功，0表示失败。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

刷新显示。当用户暂停时如果刷新了窗口，则窗口中的图像因为刷新而消失，此时调用这个接口可以重新把图像显示出来；只有在暂停和单帧播放时才会执行，其它情况会直接返回。

#### See Also

**[PlayM4_RefreshPlayEx](PlayM4_RefreshPlayEx.html)  

---**

<a id="sec_088"></a>
#### PlayM4_RefreshPlayEx

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_RefreshPlayEx*

刷新显示（多显示区域）。

```
int PlayM4_RefreshPlayEx(
  int             nPort,
  unsigned int    nRegionNum
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

*nRegionNum*
:   [in] 显示区域序号

#### Return Values

1表示成功，0表示失败。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

刷新显示，同PlayM4_RefreshPlay。为支持PlayM4_SetDisplayRegion而增加一个参数。

当前版本暂不支持此接口。

#### See Also

**[PlayM4_RefreshPlay](PlayM4_RefreshPlay.html)  

---**

<a id="sec_089"></a>
#### PlayM4_SetDisplayType

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_SetDisplayType

设置显示模式。

```
int PlayM4_SetDisplayType(
  int    nPort,
  int    nType
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

*nType*
:   [in] 几种模式，详见“Remarks”说明

#### Remarks

不同模式对应不同的显示模式，如下表所示：

| nType宏定义 | nType含义 | 宏定义值 |
| --- | --- | --- |
| **DISPLAY_NORMAL** | 正常分辨率数据送显卡显示 | 0x00000001 |
| **DISPLAY_QUARTER** | 1/4分辨率数据送显卡显示 | 0x00000002 |
| **DISPLAY_NOTEARING** | 无显示撕裂效果 | 0x00000008 |

设置显示的模式，在小画面显示时，采用DISPLAY_QUARTER 可以减小显卡工作量，从而支持更多路显示，但画面显示质量有下降。在正常和大画面显示时应该使用DISPLAY_NORMAL。

nType是按位表示的，3就是1和2同时设置。

正常显示DISPLAY_NORMAL和1/4显示DISPLAY_QUARTER 不能同时设置，其他可以组合使用。

#### Return Values

成功返回1；失败返回0。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### See Also

**[PlayM4_GetDisplayType](PlayM4_GetDisplayType.html)  

---**

<a id="sec_090"></a>
#### PlayM4_GetDisplayType

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_GetDisplayType

获取显示模式。

```
int PlayM4_GetDisplayType(
  int    nPort
);
```

#### Parameters

*nPort*
:   [in]
    播放通道号

#### Return Values

显示模式，如DISPLAY_NORMAL 或 DISPLAY_QUARTER。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

以下是该接口可能返回的值

| **返回值** | 宏定义 | 返回值 |
| --- | --- | --- |
| **DISPLAY_NORMAL** | 0x00000001 | 正常分辨率数据送显卡显示。 |
| **DISPLAY_QUARTER** | 0x00000002 | 1/4分辨率数据送显卡显示。 |
| **DISPLAY_NOTEARING** | 0x00000008 | 无显示撕裂效果。 |

#### See Also

**[PlayM4_SetDisplayType](PlayM4_SetDisplayType.html)  

---**

<a id="sec_091"></a>
#### PlayM4_WndResolutionChange

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_WndResolutionChange

窗口大小改变通知。

```
int PlayM4_WndResolutionChange(
  int         nPort
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

#### Return Values

成功返回1；失败返回0。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

窗口改变后必须要调用；否则可能会出现显示画面诸多问题。

<a id="sec_092"></a>
#### PlayM4_DisplayLostFrames

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_DisplayLostFrames

播放时设置显示帧率，提升性能。

```
int PlayM4_DisplayLostFrames(
  LONG      nPort,
  int      nModeType,
  int      nDisFrameRate,
  int      bFlag
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

*nModeType*
:   [in]启动模式，取值：自动nModeType为0，手动nModeType为1

*nDisFrameRate*
:   [in] 设置帧率，手动模式下设置的秒显示帧数,建议值小于视频本身帧率，大于或等于码流本身帧率实际无效果

*bFlag*
:   [in] 启动开关，当前nPort这一路是否设置或者取消显示策略配置：-取消当前nPort这一路的显示策略配置；-设置当前nPort这一路的显示策略配置。
    设置的帧率，真正显示的帧率会在设置的帧率附件浮动

#### Return Values

成功返回1；失败返回0。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

PlayM4_DisplayLostFrames只有在play后调用有效，play前调用返回失败 。

#### See Also

**[PlayM4_Play](PlayM4_Play.html)   [PlayM4_Stop](PlayM4_Stop.html)  

**[PlayM4_RenderPrivateData](PlayM4_RenderPrivateData.html)  

---****

<a id="sec_095"></a>
##### PlayM4_GetSourceBufferRemain

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_GetSourceBufferRemain

获取源缓冲区剩余数据大小。

```
unsigned int PlayM4_GetSourceBufferRemain(
  int    nPort
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

#### Return Values

获取源缓冲区剩余数据大小（BYTE），获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### See Also

**[PlayM4_SetSourceBufCallBack](PlayM4_SetSourceBufCallBack.html)   [PlayM4_ResetSourceBuffer](PlayM4_ResetSourceBuffer.html)

---**

<a id="sec_096"></a>
##### PlayM4_SetSourceBufCallBack

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_SetSourceBufCallBack*

设置源缓冲区阈值及回调指针。

```
int PlayM4_SetSourceBufCallBack(
  int                  nPort,
  unsigned int         nThreShold,
  SourceBufCallBack    fSourceBufCallBackFun,
  unsigned int         dwUser,
  void                *pReserved
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

*nThreShold*
:   [in] 阀值

*SourceBufCallBack*
:   [in] 回调函数指针

#### Callback Function

```
typedef void(CALLBACK *SourceBufCallBack)(
  int             nPort,
  ussigned int    nBufSize,
  ussigned int    dwUser,
  void           *pResvered
);
```

#### Callback Function Parameters

*nPort*
:   [out] 播放器通道号

*nBufSize*
:   [out] 缓冲区中剩余数据

*dwUser*
:   [out] 用户数据

*pResvered*
:   [out] 保留数据

*dwUser*
:   [in] 用户数据

*pReserved*
:   [in] 保留数据

#### Return Values

成功返回1；失败返回0。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

设置源缓冲区阀值和剩余数据小于等于阀值时的回调函数指针。只有在数据量从大到小"越过"指定阈值的时候, 才会触发回调;
一次触发后需要调用PlayM4_ResetSourceBufFlag接口重置参数, 使得再次有效。

当前版本暂不支持

#### See Also

**[PlayM4_ResetSourceBuffer](PlayM4_ResetSourceBuffer.html)   [PlayM4_GetSourceBufferRemain](PlayM4_GetSourceBufferRemain.html)  

---**

<a id="sec_097"></a>
##### PlayM4_ResetSourceBuffer

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_ResetSourceBuffer

清空所有缓冲区的剩余数据。

```
int PlayM4_ResetSourceBuffer(
  int    nPort
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

#### Return Values

1表示成功，0表示失败。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### See Also

**[PlayM4_GetSourceBufferRemain](PlayM4_GetSourceBufferRemain.html)   [PlayM4_SetSourceBufCallBack](PlayM4_SetSourceBufCallBack.html)

---**

<a id="sec_099"></a>
##### PlayM4_SetDisplayBuf

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_SetDisplayBuf

设置播放缓冲区最大缓冲帧数。

```
int PlayM4_SetDisplayBuf(
  int             nPort,
  unsigned int    nNum
);
```

#### Parameters

*nPort*
:   [in]
    播放通道号

*nNum*
:   [in]
    播放缓冲区最大缓冲帧数，详见“Remarks”说明

#### Remarks

不同的获取功能对应不同的结构体和命令号，如下表所示：

| nNum宏定义 | nNum含义 | 宏定义值 |
| --- | --- | --- |
| **MIN_DIS_FRAMES** | 播放缓冲区最小缓冲帧数 | 1 |
| **MAX_DIS_FRAMES** | 播放缓冲区最大缓冲帧数 | 50 |

#### Return Values

1表示成功，0表示失败。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

设置播放缓冲区（即解码后的图像缓冲区）大小；这个缓冲区比较重要，直接影响播放的流畅性和延时性。在一定范围内缓冲越大越流畅，同时延时越大，nNum为6表示自适应模式，还支持设置1、15帧的缓冲区大小；其他值无效，默认为自适应模式。

nNum参数范围：MIN_DIS_FRAMES ~MAX_DIS_FRAMES。

一帧352*288图像的所需内存最小值是 352*288*3/2大约150K 。最大值是352*288*4大约405K。

接口在PlayM4_OpenStream之后、PlayM4_Play之前调用有效。

#### See Also

**[PlayM4_GetDisplayBuf](PlayM4_GetDisplayBuf.html)

---**

<a id="sec_100"></a>
##### PlayM4_GetDisplayBuf

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_GetDisplayBuf

获取播放缓冲区最大缓冲帧数

```
unsigned int PlayM4_GetDisplayBuf(
  int    nPort
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

#### Return Values

播放缓冲区最大缓冲帧数，获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### See Also

**[PlayM4_SetDisplayBuf](PlayM4_SetDisplayBuf.html)

---**

<a id="sec_102"></a>
##### PlayM4_ResetBuffer

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_ResetBuffer

清空指定缓冲区的剩余数据。

```
int PlayM4_ResetBuffer(
  int             nPort,
  unsigned int    nBufType
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

*nBufType*
:   [in] 缓冲区类型，详见“Remarks”说明

#### Remarks

缓冲区类型，如下表所示：

| 缓冲区宏定义 | 缓冲区含义 | 宏定义值 |
| --- | --- | --- |
| **BUF_VIDEO_SRC** | 视频数据源缓冲区，缓冲解码之前视频数据，只对流模式有效，单位byte | 1 |
| **BUF_AUDIO_SRC** | 音频数据源缓冲区，缓冲解码之前音频数据，只对流模式有效，单位byte。且音视频数据分开送到情况下才有效 | 2 |
| **BUF_VIDEO_RENDER** | 解码后视频缓冲区总节点个数，以帧为单位 | 3 |
| **BUF_AUDIO_RENDER** | 解码后音频缓冲区总节点个数，以帧为单位 | 4 |
| **BUF_VIDEO_DECODED** | 解码后视频缓冲区数据节点个数，以帧为单位 | 5 |
| **BUF_AUDIO_DECODED** | 解码后音频缓冲区数据节点个数，以帧为单位 | 6 |

#### Return Values

1表示成功，0表示失败。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### See Also

**[PlayM4_ResetSourceBufFlag](PlayM4_ResetSourceBufFlag.html)   [PlayM4_GetBufferValue](PlayM4_GetBufferValue.html)

---**

<a id="sec_103"></a>
##### PlayM4_ResetSourceBufFlag

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_ResetSourceBufFlag*

重置回调标志为有效状态。

```
int PlayM4_ResetSourceBufFlag(
  int     nPort
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

#### Return Values

1表示成功，0表示失败。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

重置回调标志位为有效状态。

当前版本暂不支持此接口。

#### See Also

**[PlayM4_ResetBuffer](PlayM4_ResetBuffer.html)   [PlayM4_GetBufferValue](PlayM4_GetBufferValue.html)

---**

<a id="sec_104"></a>
##### PlayM4_GetBufferValue

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_GetBufferValue

获取指定缓冲区的大小。

```
unsigned int PlayM4_GetBufferValue(
  int             nPort,
  unsigned int    nBufType
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

*nBufType*
:   [in] 缓冲区类型，详见“Remarks”说明

#### Remarks

缓冲区类型，如下表所示：

| 缓冲区宏定义 | 缓冲区含义 | 宏定义值 |
| --- | --- | --- |
| **BUF_VIDEO_SRC** | 视频数据源缓冲区，缓冲解码之前视频数据，只对流模式有效，单位byte | 1 |
| **BUF_AUDIO_SRC** | 音频数据源缓冲区，缓冲解码之前音频数据，只对流模式有效，单位byte。且音视频数据分开送到情况下才有效 | 2 |
| **BUF_VIDEO_RENDER** | 解码后视频缓冲区总节点个数，以帧为单位 | 3 |
| **BUF_AUDIO_RENDER** | 解码后音频缓冲区总节点个数，以帧为单位 | 4 |
| **BUF_VIDEO_DECODED** | 解码后视频缓冲区数据节点个数，以帧为单位 | 5 |
| **BUF_AUDIO_DECODED** | 解码后音频缓冲区数据节点个数，以帧为单位 | 6 |

#### Return Values

根据参数不同，返回缓冲区值，源缓冲区返回byte,解码后缓冲区返回帧数。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

获取播放器中的缓冲区大小（帧数或者byte）。这个接口可以帮助用户了解缓冲区中的数据，从而在网络延时方面有所估计。

#### See Also

**[PlayM4_ResetBuffer](PlayM4_ResetBuffer.html)   [PlayM4_ResetSourceBufFlag](PlayM4_ResetSourceBufFlag.html)

---**

<a id="sec_106"></a>
#### PlayM4_SetFileRefCallBack

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_SetFileRefCallBack

设置建立索引回调。

```
int PlayM4_SetFileRefCallBack(
  int              nPort,
  FileRefDoneCB    pFileRefDone,
  unsigned int     nUser
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

*FileRefDoneCB*
:   [in] 索引回调函数

#### Callback Function

```
typedef void(CALLBACK *pFileRefDone)(
  unsigned int    nPort,
  unsigned int    nUser
);
```

#### Callback Function Parameters

*nPort*
:   [out] 播放器通道号

*nUser*
:   [out] 用户数据

*nUser*
:   [in] 用户指针

#### Remarks

建立文件索引回调。为了能在文件中准确快速的定位，在文件打开的时候生成文件索引。

这个过程耗时比较长，主要是因为从硬盘读数据比较慢。建立索引的过程是在后台完成，需要使用索引的函数要等待这个过程结束，而其他接口不会受到影响。

打开文件时是否建立文件的关键帧索引, 如果索引回调未触发, 表明录像文件异常。

#### Return Values

成功返回1；失败返回0。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### See Also

**[PlayM4_GetKeyFramePos](PlayM4_GetKeyFramePos.html)   [PlayM4_GetNextKeyFramePos](PlayM4_GetNextKeyFramePos.html)  

**[PlayM4_GetRefValue](PlayM4_GetRefValue.html)   [PlayM4_SetRefValue](PlayM4_SetRefValue.html)  

---****

<a id="sec_107"></a>
#### PlayM4_GetKeyFramePos

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_GetKeyFramePos

查找指定位置之前的关键帧位置。

```
int PlayM4_GetKeyFramePos(
  int             nPort,
  unsigned int    nValue,
  unsigned int    nType,
 FRAME_POS       *pFramePos
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

*nValue*
:   [in] 当前位置，可以是时间或帧号，类型由nType指定，详见“Remarks”说明

*nType*
:   [in] nType类型，详见“Remarks”说明

#### Remarks

不同nType取值表示不同的含义，如下表所示：

| nType取值 | nType取值含义 |
| --- | --- |
| **BY_FRAMENUM** | 如果nType 是BY_FRAMENUM，则nValue表示帧号 |
| **BY_FRAMTIME** | 如果nType 是BY_FRAMTIME，则nValue表示时间，单位毫秒 |

*pFramePos*
:   [out] 查找到的关键帧的文件位置、帧序号、时标信息

#### Return Values

成功返回1；失败返回0。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

查找指定位置之前的关键帧位置。图像解码必须从关键帧开始，如果用户保存的文件不是从关键帧开始的，那么到下一个关键帧之前的数据会被忽略。如果用户要截取文件中的一段数据，则应该考虑从关键帧开始截取。结束位置则关系不大，最多丢失3帧数据。

#### See Also

**[PlayM4_GetNextKeyFramePos](PlayM4_GetNextKeyFramePos.html)  

**[PlayM4_GetRefValue](PlayM4_GetRefValue.html)   [PlayM4_SetRefValue](PlayM4_SetRefValue.html)  

---****

<a id="sec_108"></a>
#### PlayM4_GetNextKeyFramePos

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_GetNextKeyFramePos

查找指定位置之后的关键帧位置。

```
int PlayM4_GetNextKeyFramePos(
  int             nPort,
  unsigned int    nValue,
  unsigned int    nType,
 FRAME_POS       *pFramePos
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

*nValue*
:   [in] 当前位置，可以是时间或帧号，类型由nType指定，详见“Remarks”说明

*nType*
:   [in] nType类型，详见“Remarks”说明

#### Remarks

不同nType取值表示不同的含义，如下表所示：

| nType取值 | nType取值含义 |
| --- | --- |
| **BY_FRAMENUM** | 如果nType 是BY_FRAMENUM，则nValue表示帧号 |
| **BY_FRAMTIME** | 如果nType 是BY_FRAMTIME，则nValue表示时间，单位毫秒 |

*pFramePos*
:   [out] 查找到的关键帧的文件位置、帧序号、时标信息

#### Return Values

成功返回1；失败返回0。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

查找指定位置之后的关键帧位置。

#### See Also

**[PlayM4_GetKeyFramePos](PlayM4_GetKeyFramePos.html)  

**[PlayM4_GetRefValue](PlayM4_GetRefValue.html)   [PlayM4_SetRefValue](PlayM4_SetRefValue.html)  

---****

<a id="sec_109"></a>
#### PlayM4_GetRefValue

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_GetRefValue

获取文件索引。

```
int PlayM4_GetRefValue(
  int               nPort,
  unsigned char    *pBuffer,
  unsigned int     *pSize
);
```

#### Parameters

*nPort*
:   [in]
    播放通道号

**pBuffer*
:   [out]
    索引信息

*pSize*
:   [out]
    输入pBuffer的大小，输出索引信息大小

#### Return Values

成功返回1；失败返回0。获取错误码调用**[NET_DVR_GetLastError](../接口定义/NET_DVR_GetLastError.html)**。

#### Remarks

获取文件索引信息，以便下次打开同一个文件时直接使用这个信息。必须在索引建成后才能获得信息。

可以在第一次指定*pSize=0,pBuffer=NULL,从*pSize的返回值获得需要的缓冲区大小。然后分配足够的缓冲，再调用一次。

smart码流获取索引需要使用PlayM4_GetRefValueEx接口；PlayM4_GetRefValue接口是针对非smart码流获取索引。

#### See Also

**[PlayM4_SetRefValue](PlayM4_SetRefValue.html)  

**[PlayM4_GetNextKeyFramePos](PlayM4_GetNextKeyFramePos.html)  

---****

<a id="sec_110"></a>
#### PlayM4_GetRefValueEx

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_GetRefValueEx

获取文件索引。

```
int PlayM4_GetRefValueEx(
  int               nPort,
  unsigned char    *pBuffer,
  unsigned int     *pSize
);
```

#### Parameters

*nPort*
:   [in]
    播放通道号

**pBuffer*
:   [out]
    索引信息

*pSize*
:   [out]
    输入pBuffer的大小，输出索引信息大小

#### Return Values

成功返回1；失败返回0。获取错误码调用**[NET_DVR_GetLastError](../接口定义/NET_DVR_GetLastError.html)**。

#### Remarks

获取文件索引信息，以便下次打开同一个文件时直接使用这个信息。必须在索引建成后才能获得信息。

smart码流获取索引需要使用PlayM4_GetRefValueEx接口；PlayM4_GetRefValue接口是针对非smart码流获取索引。

可以在第一次指定*pSize=0,pBuffer=NULL,从*pSize的返回值获得需要的缓冲区大小。然后分配足够的缓冲，再调用一次。

#### See Also

**[PlayM4_SetRefValue](PlayM4_SetRefValue.html)  

**[PlayM4_GetNextKeyFramePos](PlayM4_GetNextKeyFramePos.html)  

---****

<a id="sec_111"></a>
#### PlayM4_SetRefValue

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_SetRefValue

设置文件索引。

```
int PlayM4_SetRefValue(
  int               nPort,
  unsigned char    *pBuffer,
  unsigned int      nSize
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

*pBuffer*
:   [in] 索引信息

*nSize*
:   [in] 索引信息的长度

#### Return Values

成功返回1；失败返回0。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

设置文件索引。如果已经有了文件索引信息，可以不再调用生成索引的回调函数PlayM4_SetFileRefCallBack，直接输入索引信息。

索引信息及其长度必须准确，在PlayM4_OpenFile之后调用。

#### See Also

**[PlayM4_GetRefValue](PlayM4_GetRefValue.html)  

**[PlayM4_GetNextKeyFramePos](PlayM4_GetNextKeyFramePos.html)  

---****

<a id="sec_113"></a>
#### PlayM4_SetDisplayCallBack

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_SetDisplayCallBack*

显示回调。

```
int PlayM4_SetDisplayCallBack(
  int          nPort,
  CALLBACK    *DisplayCBFun
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

*DisplayCBFun*
:   [in] 显示回调函数，若不需要回调函数则可以为NULL，否则不能置为NULL

#### Callback Function

```
typedef void(CALLBACK *DisplayCBFun)(
  int      nPort,
  char    *pBuf,
  int      nSize,
  int      nWidth,
  int      nHeight,
  int      nStamp,
  int      nType,
  int      nReceved
);
```

#### Callback Function Parameters

*nPort*
:   [out] 播放器通道号

*pBuf*
:   [out] 返回图像数据的指针

*nSize*
:   [out] 返回图像数据大小

*nWidth*
:   [out] 画面宽，单位像素

*nHeigh*
:   [out] 画面高

*nStamp*
:   [out] 时标信息，单位毫秒

*nType*
:   [out] 数据类型， T_YV12，T_RGB32，T_UYVY，详见PlayM4_SetDecCallBack宏定义

nType数据类型，如下表所示：

| nType数据类型宏定义 | 宏定义值 | nType数据类型含义 |
| --- | --- | --- |
| **T_YV12** | 3 | 视频数据，yv12格式。排列顺序“Y0-Y1-……”，“V0-V1….”，“U0-U1-…..”。 |
| **T_UYVY** | 1 | 视频数据，uyvy格式。“U0-Y0-V0-Y1-U2-Y2-V2-Y3….”，第一个像素位于图像左上角。 |
| **T_RGB32** | 7 | 视频数据。每个像素4个字节，排列方式与位图相似，“B-G-R-0 …”，第一个像素位于图像左下角。 |
| **T_AUDIO16** | 101 | 音频数据;采样率16khz，单声道，每个采样点16位表示。具体的音频数据参数以解码后的获取的为准。 |

*nReceved*
:   [out] 保留

#### Return Values

成功返回1；失败返回0。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

设置显示回调函数；注意要尽快返回，如果要停止回调，可以把回调函数指针DisplayCBFun设为NULL。

一旦设置回调函数，则一直有效，直到程序退出。该函数可以在任何时候调用。

回调在时钟线程中触发, 不能出现耗时操作, 否则会打乱时钟脉冲, 影响显示。

#### See Also

**[PlayM4_SetDisplayCallBackEx](PlayM4_SetDisplayCallBackEx.html)   [PlayM4_SetJpegQuality](PlayM4_SetJpegQuality.html)**

**[PlayM4_ConvertToBmpFile   [PlayM4_ConvertToJpegFile](PlayM4_ConvertToJpegFile.html)](PlayM4_ConvertToBmpFile.html)**

---

<a id="sec_114"></a>
#### PlayM4_SetDisplayCallBackEx

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_SetDisplayCallBackEx

显示回调（带用户指针）。

```
int PlayM4_SetDisplayCallBackEx(
  int          nPort,
  CALLBACK    *DisplayCBFun,
  int          nUser
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

*DisplayCBFun*
:   [in] 抓图回调函数，若不需要回调函数则置为NULL,否则不能为NULL

#### Callback Function

```
typedef void(CALLBACK *DisplayCBFun)(
 DISPLAY_INFO    *pstDisplayInfo,
);
```

#### Callback Function Parameters

*pstDisplayInfo*
:   [out] 当前显示信息结构体指针

*nUser*
:   [in] 用户指针

#### Return Values

1表示成功，0表示失败。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

当前获取到的图像数据类型为YV12格式。

#### See Also

**[PlayM4_SetDisplayCallBack](PlayM4_SetDisplayCallBack.html)   [PlayM4_SetJpegQuality](PlayM4_SetJpegQuality.html)**

**[PlayM4_ConvertToBmpFile   [PlayM4_ConvertToJpegFile](PlayM4_ConvertToJpegFile.html)](PlayM4_ConvertToBmpFile.html)**

---

<a id="sec_115"></a>
#### PlayM4_ConvertToBmpFile

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_ConvertToBmpFile

图像数据转为BMP格式 。

```
int PlayM4_ConvertToBmpFile(
  char    *pBuf,
  int      nSize,
  int      nWidth,
  int      nHeight,
  int      nType,
  char    *sFileName
);
```

#### Parameters

*pBuf*
:   [in] 抓图回调函数中图像缓冲区

*nSize*
:   [in] 抓图回调函数中图像的大小

*nWidth*
:   [in] 抓图回调函数中图像宽度

*nHeight*
:   [in] 抓图回调函数中图像高度

*nType*
:   [in] 抓图回调函数中图像类型

*sFileName*
:   [in] 要保存的文件名，最好以BMP作为文件扩展名

#### Return Values

1表示成功，0表示失败。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

将解码后数据保存成BMP文件。送入的图像数据必须是YV12数据，可从解码回调或者显示回调中获取，此接口可在播放库回调函数中使用。

除YV12格式以外，其他数据类型暂不支持。

pbuf所指向的内容在函数里面不能被修改。

因为2cif过于扁长不美观，不适合预览，2cif抓图后是4CIF图像。

#### See Also

**[PlayM4_ConvertToJpegFile](PlayM4_ConvertToJpegFile.html)   [PlayM4_SetJpegQuality](PlayM4_SetJpegQuality.html)**

**[PlayM4_SetDisplayCallBack](PlayM4_SetDisplayCallBack.html)   [PlayM4_SetDisplayCallBackEx](PlayM4_SetDisplayCallBackEx.html)**

**[PlayM4_GetBMP](PlayM4_GetBMP.html)   [PlayM4_GetJPEG](PlayM4_GetJPEG.html)**

---

<a id="sec_116"></a>
#### PlayM4_ConvertToJpegFile

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_ConvertToJpegFile

图像数据转为JPEG 格式。

```
int PlayM4_ConvertToJpegFile(
  char    *pBuf,
  int      nSize,
  int      nWidth,
  int      nHeight,
  int      nType,
  char    *sFileName
);
```

#### Parameters

*pBuf*
:   [in] 抓图回调函数中图像缓冲区

*nSize*
:   [in] 抓图回调函数中图像的大小

*nWidth*
:   [in] 抓图回调函数中图像宽度

*nHeight*
:   [in] 抓图回调函数中图像高度

*nType*
:   [in] 抓图回调函数中图像类型，（当前的播放库获取的类型是yv12）

*sFileName*
:   [in] 要保存的文件名，最好以JPG作为文件扩展名

#### Return Values

1表示成功，0表示失败。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

将解码后数据保存成JPEG文件, 该函数可在回调函数中使用, 用法参见PlayM4_ConvertToBmpFile。

若图像不是16整数倍的，会裁剪至16的整数倍，如176*120抓图就会被裁剪到176*112。

pbuf所指向的内容在函数里面不能被修改。

因为2cif过于扁长不美观，不适合预览，2cif抓图后是4CIF图像。

#### See Also

**[PlayM4_ConvertToBmpFile](PlayM4_ConvertToBmpFile.html)   [PlayM4_SetJpegQuality](PlayM4_SetJpegQuality.html)**

**[PlayM4_SetDisplayCallBack](PlayM4_SetDisplayCallBack.html)   [PlayM4_SetDisplayCallBackEx](PlayM4_SetDisplayCallBackEx.html)**

**[PlayM4_GetBMP](PlayM4_GetBMP.html)   [PlayM4_GetJPEG](PlayM4_GetJPEG.html)**

---

<a id="sec_117"></a>
#### PlayM4_GetBMP

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_GetBMP

直接抓取BMP图像。

```
int PlayM4_GetBMP(
  int                nPort,
  unsigned char *    pBitmap,
  unsigned int       nBufSize,
  unsigned int*      pBmpSize
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

*pBitmap*
:   [in] 存放BMP图像数据地址，由用户分配，不得小于bmp图像大小，即sizeof(BITMAPFILEHEADER) + sizeof(BITMAPINFOHEADER) + w * h * 4， 其中w和h分别为图像宽高

*nBufSize*
:   [in] 申请的缓冲区大小

*pBmpSize*
:   [out] 获取到的实际bmp图像大小

#### Return Values

1表示成功，0表示失败。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

获取的数据为一帧bmp数据，写成文件即可用图片浏览工具查看。

pbuf所指向的内容在函数里面不能被修改。

因为2cif过于扁长不美观，不适合预览，2cif抓图后是4CIF图像。

#### See Also

**[PlayM4_GetJPEG](PlayM4_GetJPEG.html)   [PlayM4_ConvertToJpegFile](PlayM4_ConvertToJpegFile.html)  

**[PlayM4_ConvertToBmpFile](PlayM4_ConvertToBmpFile.html)  

---****

<a id="sec_118"></a>
#### PlayM4_GetJPEG

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_GetJPEG

直接抓取JPEG图像。

```
int PlayM4_GetJPEG(
  int               nPort,
  unsigned char*    pJpeg,
  unsigned int      nBufSize,
  unsigned int*     pJpegSize
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

*pJpeg*
:   [in] 存放JEPG图像数据地址，由用户分配，不得小于JPEG图像大小，建议大小w * h * 3/2， 其中w和h分别为图像宽高

*nBufSize*
:   [in] 申请的缓冲区大小

*pJpegSize*
:   [out] 获取到的实际JPEG图像数据大小

#### Return Values

1表示成功，0表示失败。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

获取的数据为一帧JPEG数据，写成文件即可用图片浏览工具查看。

若图像不是16整数倍的，会裁剪至16的整数倍，如176*120抓图就会被裁剪到176*112。

pbuf所指向的内容在函数里面不能被修改。

因为2cif过于扁长不美观，不适合预览，2cif抓图后是4CIF图像。

#### See Also

**[PlayM4_ConvertToBmpFile](PlayM4_ConvertToBmpFile.html)   [PlayM4_ConvertToJpegFile](PlayM4_ConvertToJpegFile.html)  

**[PlayM4_GetBMP](PlayM4_GetBMP.html)  

---****

<a id="sec_119"></a>
#### PlayM4_SetJpegQuality

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_SetJpegQuality

设置JPEG图像质量。

```
int PlayM4_SetJpegQuality(
  int    nQuality
);
```

#### Parameters

*nQuality*
:   [in] 图像质量参数，范围0~100

#### Return Values

成功返回1；失败返回0。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

设置抓取的JPEG图像质量, 设置范围0~100, 建议使用75~90, 若不调用该函数, 则采用默认图像质量, 目前默认为80。

需要在抓图进行前调用，建议在PlayM4_OpenFile之前使用。

有效值范围（0~100）外的都取默认值80，且不报错。

#### See Also

**[PlayM4_ConvertToJpegFile](PlayM4_ConvertToJpegFile.html)   [PlayM4_GetJPEG](PlayM4_GetJPEG.html)

**[PlayM4_GetCropJPEG](PlayM4_GetCropJPEG.html)  

---****

<a id="sec_121"></a>
#### PlayM4_RegisterDrawFun

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_RegisterDrawFun

画图回调。

```
int PlayM4_RegisterDrawFun(
  int          nPort,
  CALLBACK   *DrawFun,
  void*       nUser
);
```

#### Parameters

*nPort*
:   [in] 播放通道号。

*DrawFun*
:   [in] 画图回调函数

#### Callback Function

```
typedef void(CALLBACK *DrawFun)(
  int          nPort,
  PLAYM4_HDC  hDc,
  void*        nUser
);
```

#### Callback Function Parameters

*nPort*
:   [out] 播放器通道号

*hDc*
:   [out] 保留参数

*nUser*
:   [out] 用户数据，就是上面输入的用户数据

*nUser*
:   [in] 用户指针

#### Return Values

成功返回1；失败返回0。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

回调在时钟线程中触发, 不能出现耗时操作, 否则会打乱时钟脉冲, 影响显示。

调用此接口，且在回调函数中做了一定处理会影响显示效率和效果。

---

<a id="sec_123"></a>
#### PlayM4_ReversePlay

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_ReversePlay

开始倒放。

```
int PlayM4_ReversePlay(
  int    nPort
);
```

#### Parameters

*nPort*
:   [in]
    播放通道号

#### Return Values

1表示成功，0表示失败。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

- 该接口必须在PlayM4_Play之后调用。
- 倒放不播放音频。分辨率大于等于1080P时，倒放的GOP只能存放25帧，所以I帧间隔大于25时，会有卡顿。
- 文件模式(PlayM4_OpenFile)下倒放前需要创建文件索引，支持最大倒放速度比正放最大速度要慢。暂不支持TS封装文件。
- 流播放模式(PlayM4_OpenStream)时，实时流数据播放不支持倒放。非实时流数据，即录像文件以读取数据方式然后送入到播放库中以流模式播放，可以实现倒放，但是应用层送入解码的数据必须是一个GOP，且是逆序送入的数据，即将录像文件先解析出GOP，然后根据GOP的时序，逆序的送入到海康播放库中。如本地PC上的录像文件，客户自己读取录像文件数据分析出各个GOP(一般指I帧机器后面依靠该I帧解码的其他帧），文件时间顺序为I1PPPPPPP..., I2PPPPPPP...,I3PPPPPPPP...,......,InPPPPPPP...，则送入到播放库中倒放需要按照InPPPPP...,In-1PPPPP...,......,I3PPPPPPP...,I2PPPPPP...,I1PPPPPP...的顺序依次送入。

![](images/文件流倒放流程图.jpg)

#### See Also

**[PlayM4_SetFileRefCallBack](PlayM4_SetFileRefCallBack.html)  

**[PlayM4_GetSystemTime](PlayM4_GetSystemTime.html)  

---****

<a id="sec_125"></a>
#### PlayM4_SetSycGroup

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_SetSycGroup

同步回放接口。

```
int PlayM4_SetSycGroup(
  int             nPort,
  unsigned int    dwGroupIndex
);
```

#### Parameters

*nPort*
:   [in]
    播放通道号

*dwGroupIndex*
:   [in]
    同步组序号，取值在0~3之间

#### Return Values

1表示成功，0表示失败。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

可以多次调用将指定的nPort加入到同步组中；

PlayM4_SetSycGroup在PlayM4_Play之前调用；

dwGroupIndex一个序号被视为一个同步组，每个同步组最多16个播放通道，若超过16给播放通道则返回失败，且必须PlayM4_FreePort此播放通道才能退出同步组；

目前只支持海康设备码流。

支持文件模式和文件流模式同步回放。

做播放控制的时候，属于同步组内的通道都需要同时下一样的操作命令。

通道在播放过程中，允许动态加入和退出同步组。

停止后不自动退出同步组，关闭后自动退出同步组。

#### See Also

**[PlayM4_SetSycStartTime](PlayM4_SetSycStartTime.html)  

---**

<a id="sec_126"></a>
#### PlayM4_GetSupplementaryTimeZone

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_GetSupplementaryTimeZone

获取当前路设置过的同步回放码流时区(实际为时差，精确到秒)。

```
BOOL PlayM4_GetSupplementaryTimeZone(
  int                  nPort,
  int                 * pTimeZone
);
```

#### Parameters

*nPort*
:   [in]
    播放通道号

*pTimeZone*
:   [out]
    时区值

#### Return Values

成功返回1；失败返回0。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

没有设置时区，获取时区报错。

设置的时区对关流后仍然有效（特殊处理）。

#### See Also

**[PlayM4_SetSupplementaryTimeZone](PlayM4_SetSupplementaryTimeZone.html)  

---**

<a id="sec_127"></a>
#### PlayM4_SetSupplementaryTimeZone

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_SetSupplementaryTimeZone

设置同步回放码流时区(实际为时差，精确到秒)。

```
BOOL PlayM4_SetSupplementaryTimeZone(
  int                  nPort,
  int                  nTimeZone
);
```

#### Parameters

*nPort*
:   [in]
    播放通道号

*nTimeZone*
:   [in]
    时区（秒为单位）取值范围为[-46800 ~ 50400]，默认初始值是0

#### Return Values

成功返回1；失败返回0。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

在同步回放接口之前调用这个接口。

每路同步回放前设置每路的时区，否则为之前默认为0时区。时区的表示以秒为单位，东区为正，西区为负。

根据时区换算到0时区的全局时间进行同步回放。

设置的时区间隔小于码流总时长(以2路一样的码流文件为例)，文件和文件流模式都是按照间隔来播放，当设置的时区间隔大于码流总时长，文件模式是早的一路播放完后迟的一路立即播放，
文件流模式为继续等待时间间隔到了才播放(没有设置流结束标记的情况下)。

不设置时区时，默认每路都在同一时区，相当于都在0时区。nTimeZone范围为[-13*60*60 ~ 14*60*60]包含边界值。

新增修改此接口设置的时区对关流后仍然有效（特殊处理）

#### See Also

**[PlayM4_GetSupplementaryTimeZone](PlayM4_GetSupplementaryTimeZone.html)  

---**

<a id="sec_129"></a>
#### PlayM4_FEC_Enable

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_FEC_Enable

设置播放显示模式。

```
int PlayM4_FEC_Enable(
  int    nPort
);
```

#### Parameters

*nPort*
:   [in]
    播放通道号

#### Return Values

成功返回1；失败返回0。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### See Also

**[PlayM4_FEC_GetPort](PlayM4_FEC_GetPort.html)   [PlayM4_FEC_DelPort](PlayM4_FEC_DelPort.html)  

**[PlayM4_FEC_SetParam](PlayM4_FEC_SetParam.html)   [PlayM4_FEC_GetParam](PlayM4_FEC_GetParam.html)  

**[PlayM4_FEC_Disable](PlayM4_FEC_Disable.html)

---******

<a id="sec_130"></a>
#### PlayM4_FEC_Disable

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_FEC_Disable

关闭鱼眼模块接口。

```
int PlayM4_FEC_Disable(
  int    nPort
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

#### Return Values

成功返回1；失败返回0。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### See Also

**[PlayM4_FEC_GetPort](PlayM4_FEC_GetPort.html)   [PlayM4_FEC_DelPort](PlayM4_FEC_DelPort.html)  

**[PlayM4_FEC_SetParam](PlayM4_FEC_SetParam.html)   [PlayM4_FEC_GetParam](PlayM4_FEC_GetParam.html)  

**[PlayM4_FEC_Enable](PlayM4_FEC_Enable.html)

---******

<a id="sec_131"></a>
#### PlayM4_FEC_GetPort

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_FEC_GetPort

获取鱼眼矫正处理子端口。

```
BOOL PlayM4_FEC_GetPort(
  LONG              nPort,
  unsigned int     *nSubPort,
  FECPLACETYPE      emPlaceType,
  FECCORRECTTYPE    emCorrectType
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

*nSubPort*
:   [in] 处理子端口

*emPlaceType*
:   [in] 安装方式

    ```
    enum tagFECPlaceType{
      FEC_PLACE_WALL    = 0x1,     //壁装方式（法线水平）
      FEC_PLACE_FLOOR   = 0x2,     //地面安装(法线向上）
      FEC_PLACE_CEILING = 0x3      //顶装方式(法线向下）
    }FECPLACETYPE
    ```

*emCorrectType*
:   [in] 矫正方式

    ```
    enum tagFECCorrectType{
      FEC_CORRECT_NULL                 = 0x0,      //不矫正
      FEC_CORRECT_PTZ                  = 0x100,    //PTZ        
      FEC_CORRECT_180                  = 0x200,    //180度矫正（对应2P）
      FEC_CORRECT_360                  = 0x300,    //360全景矫正（对应1P）
      FEC_CORRECT_LAT                  = 0x400,     //纬度展开
      FEC_CORRECT_SEMISPHERE           = 0x500,     //3D矫正-（可以开多路）
      FEC_CORRECT_CYLINDER             = 0x0600,    // 鱼眼圆柱显示 - 顶装/底装
      FEC_CORRECT_CYLINDER_SPLIT       = 0x0700, // 鱼眼切开的圆柱显示 - 顶装/底装
      FEC_CORRECT_PLANET               = 0x0800, // 鱼眼小行星
      FEC_CORRECT_ARCSPHERE_HORIZONTAL = 0x0900, // 鱼眼水平弧面 - 壁装
      FEC_CORRECT_ARCSPHERE_VERTICAL   = 0x0A00, // 鱼眼垂直弧面 - 壁装
    }FECCORRECTTYPE
    ```

#### Return Values

成功返回TRUE；失败返回FALSE。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

壁装不支持180矫正，并且壁装方式不支持更新180和360度矫正时的偏移角度，壁装方式360度矫正和纬度矫正效果一致。

鱼眼不支持画面旋转。

FEC_CORRECT_NULL、FEC_CORRECT_PTZ、FEC_CORRECT_180、FEC_CORRECT_360、FEC_CORRECT_LAT是2D鱼眼。 FEC_CORRECT_SEMISPHERE、FEC_CORRECT_CYLINDER、FEC_CORRECT_CYLINDER_SPLIT、FEC_CORRECT_PLANET、FEC_CORRECT_ARCSPHERE_HORIZONTAL和FEC_CORRECT_ARCSPHERE_VERTICAL是3D鱼眼。

顶装和底装不支持纬度展开方式。

PlayM4_FEC_SetConfig不建议使用的FEC_DISPLAYSPHERE；建议使用新的鱼眼球面矫正方式PlayM4_FEC_GetPort中设定emCorrectType为FEC_CORRECT_SEMISPHERE。

同一路鱼眼只有一种安装方式，且不支持全景、纬度、原图同时开启。

水平（垂直）鱼眼弧面展开时，若圆心参数left小于0或right大于1（top<0或bottom>1），则边缘会出现拉伸模糊现象。

#### See Also

**[PlayM4_FEC_Enable](PlayM4_FEC_Enable.html)   [PlayM4_FEC_Disable](PlayM4_FEC_Disable.html)  

**[PlayM4_FEC_SetParam](PlayM4_FEC_SetParam.html)   [PlayM4_FEC_GetParam](PlayM4_FEC_GetParam.html)  

**[PlayM4_FEC_DelPort](PlayM4_FEC_DelPort.html)

---******

<a id="sec_132"></a>
#### PlayM4_FEC_DelPort

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_FEC_DelPort

删除鱼眼矫正处理子端口。

```
int PlayM4_FEC_DelPort(
  int    nPort,
  int    nSubPort
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

*nSubPort*
:   [in] 处理子端口

#### Return Values

成功返回1；失败返回0。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### See Also

**[PlayM4_FEC_GetPort](PlayM4_FEC_GetPort.html)

**[PlayM4_FEC_Enable](PlayM4_FEC_Enable.html)   [PlayM4_FEC_Disable](PlayM4_FEC_Disable.html)  

**[PlayM4_FEC_SetParam](PlayM4_FEC_SetParam.html)   [PlayM4_FEC_GetParam](PlayM4_FEC_GetParam.html)  

---******

<a id="sec_133"></a>
#### PlayM4_FEC_SetParam

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_FEC_SetParam

设置鱼眼矫正参数。

```
int PlayM4_FEC_SetParam(
  int                 nPort,
  unsigned int         nSubPort,
  FISHEYEPARAM        *pPara
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

*nSubPort*
:   [in] 处理子端口

*pPara*
:   [in] 鱼眼矫正参数结构体参数指针

#### Return Values

成功返回1；失败返回0。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

CYCLEPARAM参数现在已经不判断四个值的范围，只要满足 左<右 并且 上<下就可以了。

鱼眼圆心参数对所有的子port号都是有效的，设置一路子port鱼眼参数，则其他路鱼眼矫正图像都会发生变化。

由鱼眼圆心参数计算的圆心点，归一化后应该是（0.5,0.5）,同时圆心参数所包含的鱼眼原图是一个实际的圆形。

360全景+PTZ模式下，不支持矫正360画面（设置fWideScanOffset）。这种模式下，矫正360画面与拖动PTZ框互斥。

低帧率码流和文件进行鱼眼矫正，矫正PTZ画面时，PTZ图框需要等到下一帧才发生变化。

非PTZ模式下不支持PTZ位置参数设置。

矫正方式有360度、180度、PTZ和纬度拉伸4种模式。

鱼眼PTZ颜色以及透明度范围是0~255；透明度Alpha参数设置鱼眼库实际无效果。

水平表面初始圆心参数范围是(0.05, 0.95, -0.3, 1.3)，垂直表面初始圆心参数范围是(-0.16, 1.16, 0.005, 0.995)。

| 参数 | 取值范围 |
| --- | --- |
| **左/上** | [-0.5, 0.4] |
| **右/下** | [0.6, 1.5] |
| **左+右/上+下** | [0.8, 1.2] |

#### See Also

**[PlayM4_FEC_GetParam](PlayM4_FEC_GetParam.html)**

**[PlayM4_FEC_Enable](PlayM4_FEC_Enable.html)   [PlayM4_FEC_Disable](PlayM4_FEC_Disable.html)**

**[PlayM4_FEC_GetPort](PlayM4_FEC_GetPort.html)   [PlayM4_FEC_DelPort](PlayM4_FEC_DelPort.html)**

---

<a id="sec_134"></a>
#### PlayM4_FEC_GetParam

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_FEC_GetParam

获取鱼眼矫正参数。

```
int PlayM4_FEC_GetParam(
  int             nPort,
  int             nSubPort,
 FISHEYEPARAM    *pPara
);
```

#### Parameters

*nPort*
:   [in]
    播放通道号。

*nSubPort*
:   [in]
    处理子端口

*pPara*
:   [in]
    鱼眼矫正参数结构体参数指针

#### Return Values

成功返回1；失败返回0。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

Linux渲染库默认情况下鱼眼矫正画面不裁剪。

#### See Also

**[PlayM4_FEC_SetParam](PlayM4_FEC_SetParam.html)

**[PlayM4_FEC_Enable](PlayM4_FEC_Enable.html)   [PlayM4_FEC_Disable](PlayM4_FEC_Disable.html)  

**[PlayM4_FEC_GetPort](PlayM4_FEC_GetPort.html)   [PlayM4_FEC_DelPort](PlayM4_FEC_DelPort.html)  

---******

<a id="sec_135"></a>
#### PlayM4_FEC_SetWnd

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_FEC_SetWnd

设置显示窗口，可以随时切换。

```
int PlayM4_FEC_SetWnd(
  int    nPort,
  int    nSubPort,
  void  *hWnd
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

*nSubPort*
:   [in] 处理子端口

*hWnd*
:   [in] 设置显示窗口句柄

#### Return Values

成功返回1；失败返回0。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

Linux渲染库默认情况下鱼眼矫正画面不裁剪。

#### See Also

**[PlayM4_FEC_Enable](PlayM4_FEC_Enable.html)   [PlayM4_FEC_Disable](PlayM4_FEC_Disable.html)  

**[PlayM4_FEC_GetPort](PlayM4_FEC_GetPort.html)   [PlayM4_FEC_DelPort](PlayM4_FEC_DelPort.html)  

**[PlayM4_FEC_SetParam](PlayM4_FEC_SetParam.html)   [PlayM4_FEC_GetParam](PlayM4_FEC_GetParam.html)  

---******

<a id="sec_136"></a>
#### PlayM4_FEC_SetCallBack

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_FEC_SetCallBack

设置鱼眼窗口的画图回调。

```
int PlayM4_FEC_SetCallBack(
  int                  nPort,
  int                  nSubPort,
  FISHEYE_CallBack    *cbFunc,
  void                *pUser
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

*nSubPort*
:   [in] 处理子端口

*cbFunc*
:   [in] 鱼眼窗口画图回调函数

#### Callback Function

```
typedef void(FISHEYE_CallBack *cbFunc)(
  void           *pUser,
  unsigned int    nSubPort,
  unsigned int    nCBType,
  void           *hDC,
  unsigned int    nWidth,
  unsigned int    nHeight
);
```

#### Callback Function Parameters

*pUser*
:   [out] 用户指针

*nSubPort*
:   [out] 处理子端口

*nCBType*
:   [out] 鱼眼的画图回调类型（暂时不支持）

*hDC*
:   [out] 保留参数

*nWidth*
:   [out] 回调返回的0

*nHeigh*
:   [out] 回调返回的0

*pUser*
:   [in] 用户指针

#### Return Values

成功返回1；失败返回0。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### See Also

**[PlayM4_FEC_Enable](PlayM4_FEC_Enable.html)   [PlayM4_FEC_Disable](PlayM4_FEC_Disable.html)  

**[PlayM4_FEC_GetPort](PlayM4_FEC_GetPort.html)   [PlayM4_FEC_DelPort](PlayM4_FEC_DelPort.html)  

**[PlayM4_FEC_SetParam](PlayM4_FEC_SetParam.html)   [PlayM4_FEC_GetParam](PlayM4_FEC_GetParam.html)  

---******

<a id="sec_137"></a>
#### PlayM4_FEC_Capture

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_FEC_Capture

鱼眼抓图。

```
int PlayM4_FEC_Capture(
  int                nPort,
  unsigned int       nSubPort,
  unsigned int       nType,
  char              *pFileName
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

*nSubPort*
:   [in] 处理子端口

*nType*
:   [in] 抓图类型

*pFileName*
:   [in] 图片保存文件名

#### Return Values

成功返回1；失败返回0。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

鱼眼抓图的分辨率是内部指定，且通常宽高是4的倍数。

支持JPEG格式抓图。

#### See Also

**[PlayM4_FEC_GetParam](PlayM4_FEC_GetParam.html)**

**[PlayM4_FEC_Enable](PlayM4_FEC_Enable.html)   [PlayM4_FEC_Disable](PlayM4_FEC_Disable.html)**

**[PlayM4_FEC_GetPort](PlayM4_FEC_GetPort.html)   [PlayM4_FEC_DelPort](PlayM4_FEC_DelPort.html)**

---

<a id="sec_138"></a>
#### PlayM4_FEC_GetCurrentPTZPort

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_FEC_GetCurrentPTZPort

获取当前选择鱼眼子port功能。

```
int PlayM4_FEC_GetCurrentPTZPort(
  int                   nPort,
  float                 fPositionX,
  float                 fPositionY,
  unsigned int         *pnPort
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

*fPositionX*
:   [in] 鼠标x位置（接触屏幕点x坐标）

*fPositionY*
:   [in] 鼠标y位置（接触屏幕点y坐标）

*pnPort*
:   [out] 子port号

#### Return Values

成功返回1；失败返回0。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### See Also

**[PlayM4_FEC_GetParam](PlayM4_FEC_GetParam.html)   [PlayM4_FEC_SetParam](PlayM4_FEC_SetParam.html)**

**[PlayM4_FEC_Enable](PlayM4_FEC_Enable.html)   [PlayM4_FEC_Disable](PlayM4_FEC_Disable.html)**

**[PlayM4_FEC_GetPort](PlayM4_FEC_GetPort.html)   [PlayM4_FEC_DelPort](PlayM4_FEC_DelPort.html)**

**[PlayM4_FEC_SetCurrentPTZPort](PlayM4_FEC_SetCurrentPTZPort.html)**

---

<a id="sec_139"></a>
#### PlayM4_FEC_SetCurrentPTZPort

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_FEC_SetCurrentPTZPort

设置当前选择鱼眼子port功能。

```
int PlayM4_FEC_SetCurrentPTZPort(
  int                  nPort,
  unsigned int         nSubPort
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

*nSubPort*
:   [in] 设置期望的子port号

#### Return Values

成功返回1；失败返回0。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### See Also

**[PlayM4_FEC_GetParam](PlayM4_FEC_GetParam.html)   [PlayM4_FEC_SetParam](PlayM4_FEC_SetParam.html)**

**[PlayM4_FEC_Enable](PlayM4_FEC_Enable.html)   [PlayM4_FEC_Disable](PlayM4_FEC_Disable.html)**

**[PlayM4_FEC_GetPort](PlayM4_FEC_GetPort.html)   [PlayM4_FEC_DelPort](PlayM4_FEC_DelPort.html)**

**[PlayM4_FEC_GetCurrentPTZPort](PlayM4_FEC_GetCurrentPTZPort.html)**

---

<a id="sec_140"></a>
#### PlayM4_FEC_SetPTZOutLineShowMode

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_FEC_SetPTZOutLineShowMode

画矩形或者不规则框选择接口。

```
int PlayM4_FEC_SetPTZOutLineShowMode(
  int                   nPort,
  FECSHOWMODE           nPTZShowMode
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

*nPTZShowMode*
:   [in] 展现模式

    ```
    enum tagFECPlaceType{
      FEC_PTZ_OUTLINE_NULL     ,     //不显示
      FEC_PTZ_OUTLINE_RECT    ,     //矩形显示
      FEC_PTZ_OUTLINE_RANGE       //真实区域显示
    }FECPLACETYPE
    ```

#### Return Values

成功返回1；失败返回0。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

鱼眼矫正在原图上画矫正区域，需要用鱼眼方式开一个没有矫正效果（FEC_CORRECT_NULL）的窗口，再开其他PTZ矫正窗口。

鱼眼ptz矫正画矫正区域，原区域和矩形区域可能效果相差大，因为矩形框只是为了标记中心位置，所以存在这样的差异。

#### See Also

**[PlayM4_FEC_GetParam](PlayM4_FEC_GetParam.html)   [PlayM4_FEC_SetParam](PlayM4_FEC_SetParam.html)**

**[PlayM4_FEC_Enable](PlayM4_FEC_Enable.html)   [PlayM4_FEC_Disable](PlayM4_FEC_Disable.html)**

**[PlayM4_FEC_GetPort](PlayM4_FEC_GetPort.html)   [PlayM4_FEC_DelPort](PlayM4_FEC_DelPort.html)**

**[PlayM4_FEC_GetCurrentPTZPort](PlayM4_FEC_GetCurrentPTZPort.html)   [PlayM4_FEC_SetCurrentPTZPort](PlayM4_FEC_SetCurrentPTZPort.html)**

---

<a id="sec_141"></a>
#### PlayM4_FEC_GetViewParam

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_FEC_GetViewParam

获取3D矫正视角参数。

```
int PlayM4_FEC_GetViewParam(
  LONG                    nPort,
  unsigned int            nSubPort,
  PLAYM4HRVIEWPARAMTYPE   enViewParamType,
  float                   *fValue,
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

*nSubPort*
:   [in] 子通道号

*enViewParamType*
:   [in] 旋转参数

    ```
    enum tagPLAYM4HRVIEWPARAMTYPE{
      PLAYM4_HR_VPT_ROTATION_X   = 0x1   //水平旋转
      PLAYM4_HR_VPT_ROTATION_Y   = 0x2    //垂直旋转        
      PLAYM4_HR_VPT_SCALE        = 0x3    //缩放(其绝对值为浮点型0值时为放大效果，目前缩放范围是-0.8~900，-0.8也是放大效果)
    }PLAYM4HRVIEWPARAMTYPE
    ```

*fValue*
:   [out] 矫正角度

#### Return Values

若成功返回1,失败返回0。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

建议用新的3D-球面矫正画面的视角变化调节(缩放和旋转)。

PlayM4_FEC_GetViewParam缩放(其绝对值为浮点型0值时为放大效果，目前缩放范围是-0.8~900，-0.8也是放大效果)。

鱼眼3D效果说明如下：

| 鱼眼3D展开 | 坐标x | 坐标y | Scale(-0.8~900) | 示例图片 |
| --- | --- | --- | --- | --- |
| **初始值（背面剔除）** | 4.71 | 0 | 3 |  |
| **放大** | 4.71 | 0 | 2 |  |
| **缩小** | 4.71 | 0 | 4 |  |
|  | 0 | 0 | 3 |  |
|  | 1.57 | 0 | 3 |  |
|  | 3.14 | 0 | 3 |  |
|  | 3.14 | 3.14 | 3 |  |
|  | 4.07 | 0 | 3 |  |
|  | 4.07 | 1.57 | 3 |  |
|  | 4.07 | 3.14 | 3 |  |

#### See Also

**[PlayM4_FEC_Enable](PlayM4_FEC_Enable.html)   [PlayM4_FEC_Disable](PlayM4_FEC_Disable.html)  

**[PlayM4_FEC_SetParam](PlayM4_FEC_SetParam.html)   [PlayM4_FEC_GetParam](PlayM4_FEC_GetParam.html)  

**[PlayM4_FEC_SetViewParam](PlayM4_FEC_SetViewParam.html)   [PlayM4_FEC_Rotate](PlayM4_FEC_Rotate.html)  

**[PlayM4_FEC_DelPort](PlayM4_FEC_DelPort.html)

---********

<a id="sec_142"></a>
#### PlayM4_FEC_SetViewParam

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_FEC_SetViewParam

设置3D矫正视角参数。

```
int PlayM4_FEC_SetViewParam(
  LONG                    nPort,
  unsigned int            nSubPort,
  PLAYM4HRVIEWPARAMTYPE   enViewParamType,
  float                   fValue,
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

*nSubPort*
:   [in] 子通道号

*enViewParamType*
:   [in] 旋转参数

    ```
    enum tagPLAYM4HRVIEWPARAMTYPE{
      PLAYM4_HR_VPT_ROTATION_X   = 0x1   //水平旋转
      PLAYM4_HR_VPT_ROTATION_Y   = 0x2    //垂直旋转        
      PLAYM4_HR_VPT_SCALE        = 0x3    //缩放(其绝对值为浮点型0值时为放大效果，目前缩放范围是-0.8~900，-0.8也是放大效果)
    }PLAYM4HRVIEWPARAMTYPE
    ```

*fValue*
:   [in] 矫正角度，设置的值为获取值加上要偏移值

#### Return Values

若成功返回1,失败返回0。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

建议用新的3D-球面矫正画面的视角变化调节(缩放和旋转)。

鱼眼3D效果说明如下：

| 鱼眼3D展开 | 坐标x | 坐标y | Scale(-0.8~900) | 示例图片 |
| --- | --- | --- | --- | --- |
| **初始值（背面剔除）** | 4.71 | 0 | 3 |  |
| **放大** | 4.71 | 0 | 2 |  |
| **缩小** | 4.71 | 0 | 4 |  |
|  | 0 | 0 | 3 |  |
|  | 1.57 | 0 | 3 |  |
|  | 3.14 | 0 | 3 |  |
|  | 3.14 | 3.14 | 3 |  |
|  | 4.07 | 0 | 3 |  |
|  | 4.07 | 1.57 | 3 |  |
|  | 4.07 | 3.14 | 3 |  |

#### See Also

**[PlayM4_FEC_Enable](PlayM4_FEC_Enable.html)   [PlayM4_FEC_Disable](PlayM4_FEC_Disable.html)  

**[PlayM4_FEC_SetParam](PlayM4_FEC_SetParam.html)   [PlayM4_FEC_GetParam](PlayM4_FEC_GetParam.html)  

**[PlayM4_FEC_GetViewParam](PlayM4_FEC_GetViewParam.html)   [PlayM4_FEC_Rotate](PlayM4_FEC_Rotate.html)  

**[PlayM4_FEC_DelPort](PlayM4_FEC_DelPort.html)

---********

<a id="sec_143"></a>
#### PlayM4_FEC_SetDisplayRegion

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_FEC_SetDisplayRegion

鱼眼电子放大接口。

```
int PlayM4_FEC_SetDisplayRegion(
  LONG             nPort,
  unsigned int     nSubPort,
  unsigned int     nType,
  DWORD            nRegionNum,
  RECT*            pSrcRect,
  HWND             hDestWnd,
  BOOL             bEnable
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

*nSubPort*
:   [in] 鱼眼子端口

*nType*
:   [in] 鱼眼电子放大。nType设定为0，则表示鱼眼电子放大（暂时只支持鱼眼电子放大）；nType设定为1，则表示鱼眼窗口分割(暂不支持)

*nRegionNum*
:   [in] 窗口序号，暂时只支持原始窗口，即nRegionNum = 0

*pSrcRect*
:   [in] 区域归一化，乘以1000除以宽或者高（值在0~1000之间）

*hWnd*
:   [in] 窗口句柄，暂时只支持原始窗口，设置为NULL

*bEnable*
:   [in] 开启关闭开关，true则开启；如设定为false的时候，如其他参数合法，可以恢复原图。（只对不在原始窗口上电子放大有效）

#### Return Values

若成功返回1,失败返回0。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

鱼眼电子放大接口，只支持原图、180、360、维度展开且只有一个鱼眼窗口（不带PTZ显示），调用鱼眼电子放大接口在原始窗口上进行电子放大

设置电子放大归一化区域不在0-1000内返回错误码PLAYM4_PARA_OVER。

设置其他窗口报错PLAYM4_PARA_OVER。

在Windows下设置原图、180、360、维度展开的电子放大后，再去开启一路PTZ展开，则原来电子放大的窗口不再电子放大（还原为电子放大前的效果）；和Windows不同，Mac和Linux和移动端电子放大和PTZ可以同时开启。

子端口号错误PLAYM4_FEC_ERR_INVALIDPORT

窗口句柄异常或未设置鱼眼窗口，渲染类没有创建，报错PLAYM4_ORDER_ERROR

鱼眼模块没有加载PLAYM4_FEC_ERR_NOTENABLE

PlayM4_FEC_GetPort后，在PlayM4_FEC_SetWnd前调用报错PLAYM4_FEC_ERR_NOSUBPORT

#### See Also

**[PlayM4_FEC_Enable](PlayM4_FEC_Enable.html)   [PlayM4_FEC_Disable](PlayM4_FEC_Disable.html)  

**[PlayM4_FEC_GetPort](PlayM4_FEC_GetPort.html)   [PlayM4_FEC_DelPort](PlayM4_FEC_DelPort.html)  

**[PlayM4_FEC_SetParam](PlayM4_FEC_SetParam.html)   [PlayM4_FEC_GetParam](PlayM4_FEC_GetParam.html)  

---******

<a id="sec_144"></a>
#### PlayM4_FEC_SetCorrectEffect

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_FEC_SetCorrectEffect

3D鱼眼矫正背面剔除。

```
int PlayM4_FEC_SetCorrectEffect(
  LONG             nPort,
  unsigned int     nSubPort,
 FECCORRECTEFFECT  nCorrectEffect,
  float          fValue
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

*nSubPort*
:   [in] 处理子端口

*nCorrectEffect*
:   [in] 背面剔除参数

    ```
    enum tagFECCorrectEffect{
      FEC_CORRECT_EFFECT_BACK_FACE_CULLING    = 0x100,      //背面剔除：非0表示启用，为0表示不启用，建议设置整数强转浮点数
    }FECCORRECTEFFECT
    ```

*fValue*
:   [in] 剔除值，若设置为非0则表示启用；设置为0则表示不启用，建议设置整数类型强制转换为浮点数

#### Return Values

若成功返回1,失败返回0。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

暂时只有3D半球背景剔除需求，其他3D矫正暂不考虑

主要用于3D半球矫正的背景剔除；鱼眼小行星设定背面剔除无效果，3D弧面展开有效果；

2D的鱼眼无背面剔除概念，接口返回失败；

#### See Also

**[PlayM4_FEC_Enable](PlayM4_FEC_Enable.html)   [PlayM4_FEC_Disable](PlayM4_FEC_Disable.html)  

**[PlayM4_FEC_GetPort](PlayM4_FEC_GetPort.html)   [PlayM4_FEC_DelPort](PlayM4_FEC_DelPort.html)  

**[PlayM4_FEC_SetParam](PlayM4_FEC_SetParam.html)   [PlayM4_FEC_GetParam](PlayM4_FEC_GetParam.html)  

---******

<a id="sec_145"></a>
#### PlayM4_FEC_Set3DModelParam

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_FEC_Set3DModelParam

设置3D模型参数。

```
int PlayM4_FEC_Set3DModelParam(
  LONG             nPort,
  unsigned int     nSubPort,
  PLAYM4FEC3DMODELPARAM  enType,
  float          fValue
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

*nSubPort*
:   [in] 鱼眼子端口

*enType*
:   [in] 圆柱矫正的模型参数

    ```
    enum tagPLAYM4FEC3DModelParam{
      PLAYM4_FEC_3DMP_CYLINDER_HEIGHT    = 0x1,      // 圆柱模型高
      PLAYM4_FEC_3DMP_CYLINDER_RADIUS    = 0x2,      // 圆柱模型半径
    }PLAYM4FEC3DMODELPARAM
    ```

*fValue*
:   [in] 校正值，圆柱模型的高或者半径的值半径和高都默认是2；半径范围是[0.5,4],高范围是[0.5,6],都包含边界

#### Return Values

若成功返回1,失败返回0。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

暂时针对3D圆柱展开有效（设置圆柱模型的高和半径）

#### See Also

**[PlayM4_FEC_Enable](PlayM4_FEC_Enable.html)   [PlayM4_FEC_Disable](PlayM4_FEC_Disable.html)  

**[PlayM4_FEC_GetPort](PlayM4_FEC_GetPort.html)   [PlayM4_FEC_DelPort](PlayM4_FEC_DelPort.html)  

**[PlayM4_FEC_SetParam](PlayM4_FEC_SetParam.html)   [PlayM4_FEC_GetParam](PlayM4_FEC_GetParam.html)  

---******

<a id="sec_146"></a>
#### PlayM4_FEC_GetSpecialViewParam

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_FEC_GetSpecialViewParam

获取3D弧面矫正特定视角参数。

```
BOOL PlayM4_FEC_GetSpecialViewParam(
  int             nPort,
  unsigned int     nSubPort,
 PLAYM4FECSPECIALVIEWTYPE  enSVType,
 PLAYM4HRVIEWPARAMTYPE  enVPType,
  float*          fValue
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

*nSubPort*
:   [in] 鱼眼子端口

*enSVType*
:   [in] 3D弧面模型与贴边视角

    ```
    enum tagPLAYM4FECSpecialViewType{
      PLAYM4_FEC_SVT_EDGE    = 0x1,      // 弧面鱼眼模型与窗口贴边视角
    }PLAYM4FECSPECIALVIEWTYPE
    ```

*enSVType*
:   [in] 视角变化类型

    ```
    enum tagPLAYM4HRViewParamType{
      PLAYM4_HR_VPT_ROTATION_X    = 0x1,      // 水平旋转
      PLAYM4_HR_VPT_ROTATION_Y    = 0x2,      // 垂直旋转
      PLAYM4_HR_VPT_SCALE         = 0x3,      // 缩放(其绝对值为浮点型0值时为黑屏-正常效果)
    }PLAYM4HRVIEWPARAMTYPE
    ```

*fValue*
:   [out] 特定视角参数

#### Return Values

成功返回TRUE；失败返回FALSE。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

只适用于弧面，跟SetViewParam接口配合使用，快速设置调节到特定的弧面视角后调用。

#### See Also

**[PlayM4_FEC_Enable](PlayM4_FEC_Enable.html)   [PlayM4_FEC_Disable](PlayM4_FEC_Disable.html)  

**[PlayM4_FEC_GetPort](PlayM4_FEC_GetPort.html)   [PlayM4_FEC_DelPort](PlayM4_FEC_DelPort.html)  

**[PlayM4_FEC_SetParam](PlayM4_FEC_SetParam.html)   [PlayM4_FEC_GetParam](PlayM4_FEC_GetParam.html)  

---******

<a id="sec_148"></a>
#### PlayM4_RenderPrivateData

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_RenderPrivateData

显示私有数据（私有信息显示开关）。

```
int PlayM4_RenderPrivateData(
  int    nPort,
  int    nIntelType,
  int    bTrue
);
```

#### Parameters

*nPort*
:   [in]
    播放通道号

*nIntelType*
:   [in] 内部类型

    ```
    enum _PLAYM4_PRIDATA_RENDER{
      PLAYM4_RENDER_ANA_INTEL_DATA    = 0x00000001, //智能分析
      PLAYM4_RENDER_MD                = 0x00000002, //移动侦测
      PLAYM4_RENDER_ADD_POS           = 0x00000004, //POS信息后叠加
      PLAYM4_RENDER_ADD_PIC           = 0x00000008, //图片叠加信息
      PLAYM4_RENDER_FIRE_DETCET       = 0x00000010  //热成像信息
      PLAYM4_RENDER_TEM               = 0x00000020  //温度信息
    }PLAYM4_PRIDATA_RENDER
    ```

*bTrue*
:   [in] 是否显示

#### Return Values

1表示成功，0表示失败。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

此接口适用于带有私有信息的码流，若无私有信息的码流则调用此接口没有效果。其他两个是默认开启的。

linux暂不支持图片叠加信息。

测温信息接口调用方式说明如下：

**开启测温信息： 需要先调用PlayM4_RenderPrivateData，再分别调用三次PlayM4_RenderPrivateDataEx接口来开启框、线、点；也可以nSubType一次性输入7来开启点线框显示；**

**关闭测温信息： 可以调用PlayM4_RenderPrivateData关闭；也可以调用三次PlayM4_RenderPrivateDataEx接口，分别关闭框、线、点；也可以一次性nSubType一次性输入7来关闭；**

**开启火点信息： 需要先调用PlayM4_RenderPrivateData，再分别调用4次PlayM4_RenderPrivateDataEx开启火点子类型；或者一次性开启4个子类型，nSubType设置为15 == 1+2+4+8；**

**关闭火点： 可以调用PlayM4_RenderPrivateData关闭大开关；也可以调用三次小开关PlayM4_RenderPrivateDataEx，分别关闭火点4个子类型，也可以设置nSubType一次性关闭。**

**另：默认显示：智能信息、移动侦测、热成像信息默认显示；默认不显示pos和测温信息；**

**POS信息、热成像信息、部分温度信息（点和框支持），此外温度信息中的字符信息不支持旋转；**

**linux的pos信息抓图是没有pos叠加信息的，win是可以实现抓图也能抓出pos信息来的；**

#### See Also

**[PlayM4_Play](PlayM4_Play.html)   [PlayM4_Stop](PlayM4_Stop.html)  

---**

<a id="sec_149"></a>
#### PlayM4_RenderPrivateDataEx

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_RenderPrivateDataEx

显示私有数据（智能信息显示开关,热成像温度信息）。

```
int PlayM4_RenderPrivateDataEx(
  int      nPort,
  int      nIntelType,
  int      nSubType,
  int      bTrue
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

*nIntelType*
:   [in] 内部类型，按位表示，每一位表示一种私有数据类型

    ```
    enum _PLAYM4_PRIDATA_RENDER{
      PLAYM4_RENDER_ANA_INTEL_DATA    = 0x00000001, //智能分析
      PLAYM4_RENDER_MD                = 0x00000002, //移动侦测
      PLAYM4_RENDER_ADD_POS           = 0x00000004, //POS信息后叠加
      PLAYM4_RENDER_ADD_PIC           = 0x00000008, //图片叠加信息
      PLAYM4_RENDER_FIRE_DETCET       = 0x00000010  //热成像信息
      PLAYM4_RENDER_TEM               = 0x00000020  //温度信息
    }PLAYM4_PRIDATA_RENDER
    ```

*nSubType*
:   [in] 测温类型；当nIntelType为PLAYM4_RENDER_FIRE_DETCET时

    ```
    enum _PLAYM4_FIRE_ALARM{
      PLAYM4_FIRE_FRAME_DIS            = 0x00000001, //火点框显示
      PLAYM4_FIRE_MAX_TEMP             = 0x00000002, //最高温度
      PLAYM4_FIRE_MAX_TEMP_POSITION    = 0x00000004, //最高温度位置显示
      PLAYM4_FIRE_DISTANCE             = 0x00000008, //最高温度距离
    }PLAYM4_FIRE_ALARM
    ```

    当nIntelType为PLAYM4_RENDER_TEM时

    ```
    enum _PLAYM4_TEM_FLAG{
      PLAYM4_TEM_REGION_BOX            = 0x00000001, //框测温
      PLAYM4_TEM_REGION_LINE           = 0x00000002, //线测温
      PLAYM4_TEM_REGION_POINT          = 0x00000004, //点测温
    }PLAYM4_TEM_FLAG
    ```

*bTrue*
:   [in] 是否显示

#### Return Values

成功返回1；失败返回0。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

此接口适用于带有智能信息的码流，若无智能信息的码流则调用此接口没有效果。

linux暂不支持图片叠加信息。

测温信息接口调用方式说明如下：

**开启测温信息： 需要先调用PlayM4_RenderPrivateData，再分别调用三次PlayM4_RenderPrivateDataEx接口来开启框、线、点；也可以nSubType一次性输入7来开启点线框显示；**

**关闭测温信息： 可以调用PlayM4_RenderPrivateData关闭；也可以调用三次PlayM4_RenderPrivateDataEx接口，分别关闭框、线、点；也可以一次性nSubType一次性输入7来关闭；**

**开启火点信息： 需要先调用PlayM4_RenderPrivateData，再分别调用4次PlayM4_RenderPrivateDataEx开启火点子类型；或者一次性开启4个子类型，nSubType设置为15 == 1+2+4+8；**

**关闭火点： 可以调用PlayM4_RenderPrivateData关闭大开关；也可以调用三次小开关PlayM4_RenderPrivateDataEx，分别关闭火点4个子类型，也可以设置nSubType一次性关闭。**

**另：默认显示：智能信息、移动侦测、热成像信息默认显示；默认不显示pos和测温信息；**

**POS信息、热成像信息、部分温度信息（点和框支持），此外温度信息中的字符信息不支持旋转；**

**linux的pos信息抓图是没有pos叠加信息的，win是可以实现抓图也能抓出pos信息来的；**

不支持第一代火点信息显示。

第一代火点图片如下：

![](images/第一代火点.jpg)

第二代火点图片如下,如下图所示可以显示最高温度以及区域信息：

![](images/第二代火点.jpg)

#### See Also

**[PlayM4_Play](PlayM4_Play.html)   [PlayM4_Stop](PlayM4_Stop.html)  

**[PlayM4_RenderPrivateData](PlayM4_RenderPrivateData.html)  

---****

<a id="sec_150"></a>
#### PlayM4_GetStreamAdditionalInfo

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_GetStreamAdditionalInfo*

获取当前显示帧PTZ信息。

```
int PlayM4_GetStreamAdditionalInfo(
  int               lPort,
  int               lType,
  unsigned char    *pInfo,
  int              *plLen
);
```

#### Parameters

*lPort*
:   [in]
    播放通道号

*lType*
:   [in]
    需要获取的数据类型；当前只支持值为1的情况，表示获取PTZ信息

*pInfo*
:   [in] [out]
    数据信息指针

*plLen*
:   [in] [out]
    数据长度

#### Return Values

成功返回1；失败返回0。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

数据类型为1表示获取当前显示帧PTZ信息。当前信息是以特定结构体形式存储在pInfo内，plLen返回长度信息;

调用方法是先传入参数pInfo = null，此时可以获取出需要分配的内存长度plLen。然后根据上次调用接口获取的内存长度申请内存，
再次调用此接口即可从pInfo获取需要的信息。

此接口适用于球机设备生成的码流文件。

当前版本暂不支持。

---

<a id="sec_151"></a>
#### PlayM4_SetConfigFontPath

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_SetConfigFontPath

设置字符叠加的字体库路径。

```
int PlayM4_SetConfigFontPath(
  int      nPort,
  char    *pFontPath
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

*pFontPath*
:   [in] 字符叠加的字体库路径

#### Return Values

1表示成功，0表示失败。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

火点、测温智能信息需要叠加字符的智能信息需要linux系统安装有字体库，在PlayM4_Play之前调用此接口。

若使用系统默认字体库则如下方式设置：

ubuntu系统命令：sudo apt-get install fonts-arphic-ukai

ubuntu系统路径：/usr/share/fonts/truetype/arphic/ukai.ttc

centos系统命令：sudo yum install cjkuni-ukai-fonts

centos系统路径：/usr/share/fonts/cjkuni-ukai/ukai.ttc

ukai.ttc 为支持中文的字体库

如果客户使用其他的字体库，则需要通过调用此接口接口将字体库路径设置进来

#### See Also

**[PlayM4_Play](PlayM4_Play.html)   [PlayM4_Stop](PlayM4_Stop.html)  

**[PlayM4_RenderPrivateData](PlayM4_RenderPrivateData.html)  

---****

<a id="sec_153"></a>
#### PlayM4_GetD3DCapture

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_GetD3DCapture

渲染库d3d11抓图。

```
int PlayM4_GetD3DCapture(
  int             nPort,
  unsigned int     nType,
  D3D_PIC_INFO   *pstPicInfo
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

*nType*
:   [in]抓图格式。取值如下：0-jpeg格式,1-bmp格式。

*pstPicInfo*
:   [in] 抓图参数

#### Return Values

成功返回1；失败返回0。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

nType取值设定抓图格式：0-jpeg,1-bmp。

已有的抓图区别于该接口抓图，所见及所得(外面注册的画图回调绘制的信息不在抓图范围)，支持智能信息显示抓图，但是比较耗性能。画线、写字、图片叠加的相关的智能信息都可以调用该接口抓图获取。

外面设置分辨率大小进行抓图建议使用和显示窗口大小一致的分辨率进行抓图，特别是测温等字符等智能信息，效果最佳；否则会有由于分辨率不一致导致拉伸或者缩放的异常效果，属于正常。

设置窗口分辨率抓图时，宽高不得小于32，宽*高不得大于5000W分辨率。

2cif分辨率或者设置窗口大小该接口两种抓图模式JPEG抓图都为4cif， BMP抓图为2cif

渲染抓图在多轨时只会抓图单轨的宽。

#### See Also

**[PlayM4_GetPort](PlayM4_GetPort.html)   [PlayM4_FreePort](PlayM4_FreePort.html)  

**[PlayM4_SetDecodeOrDisplayMode](PlayM4_SetDecodeOrDisplayMode.html)  

---****

<a id="sec_154"></a>
#### PlayM4_GetD3DPostProcess

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_GetD3DPostProcess

d3d11图像后处理,获取参数。

```
BOOL PlayM4_GetD3DPostProcess(
  LONG             nPort,
 PLAYM4PostProcType    nPostType,
  float*           fValue
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

*nPostType*
:   [in]D3D图像后处理类型，详见Remarks说明

*fValue*
:   [out] fValue

#### Return Values

成功返回TRUE；失败返回FALSE。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

此接口Play之后调用。

D3D图像后处理类型，如下表所示：

| D3D图像后处理类型 | 宏定义值 | 说明 |
| --- | --- | --- |
| PLAYM4_PPT_BRIGHTNESS | 0x1 | 亮度，取值范围[-1.0,1.0] |
| PLAYM4_PPT_HUE | 0x2 | 色度，取值范围[0.0,1.0]（0.166累加为一种颜色变化及0和1为同一种颜色） |
| PLAYM4_PPT_SATURATION | 0x3 | 饱和度，取值范围[-1.0,1.0] |
| PLAYM4_PPT_CONTRAST | 0x4 | 对比度，取值范围[-1.0,1.0] |
| PLAYM4_PPT_SHARPNESS | 0x5 | 锐度，取值范围[0.0,1.0] |

#### See Also

**[PlayM4_GetPort](PlayM4_GetPort.html)   [PlayM4_FreePort](PlayM4_FreePort.html)  

**[PlayM4_SetDecodeOrDisplayMode](PlayM4_SetDecodeOrDisplayMode.html)  

**[PlayM4_SetD3DPostProcess](PlayM4_SetD3DPostProcess.html)  

---******

<a id="sec_155"></a>
#### PlayM4_SetD3DPostProcess

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_SetD3DPostProcess

d3d11图像后处理，设置参数。

```
BOOL PlayM4_SetD3DPostProcess(
  LONG                nPort,
  PLAYM4PostProcType nPostType,
  float              fValue
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

*nPostType*
:   [in]D3D图像后处理类型，详见Remarks说明

*fValue*
:   [in] fValue

#### Return Values

成功返回TRUE；失败返回FALSE。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

此接口Play之后调用。

此接口不支持智能信息。

D3D图像后处理类型，如下表所示：

| D3D图像后处理类型 | 宏定义值 | 说明 |
| --- | --- | --- |
| PLAYM4_PPT_BRIGHTNESS | 0x1 | 亮度，取值范围[-1.0,1.0] |
| PLAYM4_PPT_HUE | 0x2 | 色度，取值范围[0.0,1.0]（0.166累加为一种颜色变化及0和1为同一种颜色） |
| PLAYM4_PPT_SATURATION | 0x3 | 饱和度，取值范围[-1.0,1.0] |
| PLAYM4_PPT_CONTRAST | 0x4 | 对比度，取值范围[-1.0,1.0] |
| PLAYM4_PPT_SHARPNESS | 0x5 | 锐度，取值范围[0.0,1.0] |

#### See Also

**[PlayM4_GetPort](PlayM4_GetPort.html)   [PlayM4_FreePort](PlayM4_FreePort.html)  

**[PlayM4_SetDecodeOrDisplayMode](PlayM4_SetDecodeOrDisplayMode.html)  

**[PlayM4_GetD3DPostProcess](PlayM4_GetD3DPostProcess.html)  

---******

<a id="sec_157"></a>
#### PlayM4_SkipErrorData

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_SkipErrorData

码流错误直接跳至下一关键帧

```
int PlayM4_SkipErrorData(
  int    nPort,
  int    bSkip
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

*bSkip*
:   [in] 1表示码流错误时会直接跳下一个关键帧解码；0表示寻找下一帧数据解码

#### Return Values

成功返回1；失败返回0。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

如果在码流有错误的情况下，不允许出现花屏，建议可以设置成1，目前版本播放库即默认为解析错误直接跳I帧的方式。H265码流有错误时，不支持该功能，播放会出现花屏。

---

<a id="sec_159"></a>
### 常见问题解答

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK开发使用手册 |

# 关于流模式接口

## ``` Question 1 送入到播放库PlayM4_OpenStream接口报错 ```

#### Answer 1

1.检查参数是否正确，调用接口[PlayM4_OpenStream](#sec_030) ，需要确认送入正确的海康文件头（通过网络SDK中的实时流回调函数中获取的NET_DVR_SYSHEAD，
或者板卡中编码回调函数中获取的PktSysHeader类型的即为正确的文件头内容以及文件头长度）；

2.调用失败后，若返回错误码是PLAYM4_ALLOC_MEMORY_ERROR，说明内存不足，可以查看pc当前内存情况使用情况排查；

3.此路流数据操作结束后，可以调用[PlayM4_CloseStream](#sec_031) 接口关闭流回收系统资源；PlayM4_CloseStream和PlayM4_OpenStream需要配对出现。

# 流模式预览

## ``` Question 2 实时流预览有卡顿 ```

#### Answer 2

1.检查数据是否流畅，若数据不流畅则检查网络部分；

2.在Linux系统下，打开终端，输入命令 glxinfo | grep OpenGL 。能够看到具体的显卡型号，表示正确安装显卡驱动；

3.检查使用的时钟类型是否是高精度的，若是高精度时钟，建议使用[PlayM4_SetTimerType](#sec_170) 将时钟类型设置为TIMER_2；

4.由于不同的分辨率对PC的性能要求不一样，如高清分辨率对PC性能要求比较高，多路高清实时预览时可能会有卡顿现象，此时可以适当降低预览的路数；

5.检查视频当前的分辨率，缓冲区若开的太小，则可能送入数据到播放库缓冲区[PlayM4_InputData](#sec_032) 满，此时需要重复送入未送成功的数据;

建议：若为4CIF分辨率，则建议[PlayM4_OpenStream](#sec_030) 缓冲开到1.5M到2M，1.5M即1.5 * 1024 *1024。若720P则建议开到3~4M；若1080P则建议开大到6M左右；

6.建议检查[PlayM4_SetDisplayBuf](#sec_099) ，设置为15个节点即可；

7.可以将数据保存下来用海康的播放器验证，若播放卡顿，则确认在网络部分是否丢数据，若播放正常则检查送数据部分是否正常。

## ``` Question 3 实时流预览不显示图像 ```

#### Answer 3

1.确认是否有正确的数据送入到海康的播放库缓冲，且调用过[PlayM4_Play](#sec_035) 开始解码；

2.确认是否注册了解码回调不显示的回调函数[PlayM4_SetDecCallBack](#sec_163)；

3.确认是否可以正常抓取到图片；若不能抓图成功则转1，若能抓图则转4；

4.抓图成功，则连续抓图，若图片随场景和OSD有变化，则表示数据正常，则检查显示的窗口句柄是否正确；

5.可以将需要解码的数据保存为本地文件，然后用海康官网上下载的海康播放器进行播放验证，若能播放则转步骤6，若不能播放则转步骤7；

6.若可以正常播放，则检查[PlayM4_InputData](#sec_032)送数据部分是否正确；

7.若不能正常播放，则检查数据码流是否正确，若是标准码流则可以用Elecard或者VLC等标准第三方解码器进行验证；若第三方的解码器可以解码则可以将测试码流发给我们分析；若第三方的解码器不能解码则检查是否有网络丢包的现象；

8.如果实时码流是RTP封装的码流，则最好提供网络抓包文件，或者如下格式：4字节RTP包的长度+RTP数据包保存，然后发给我们确认。

## ``` Question 4 实时流预览延时 ```

#### Answer 4

1.一般设备延时在100到200ms之间，延时和网络的流畅性有很大关系。如在全帧率下延时正常，而在低帧率情况下比较明显，可以反馈给我们确认。6.2.2.2版本以后，延时会达到最小；

2.如果是多路预览才出现延时的现象，则请查看当前CPU的使用情况，可能是CPU已经达到极限（85%以上），无法支持这么多路的实时流解码，可以尝试减少几路播放，或者提高硬件性能；

3.若客户使用的是海康的客户端软件，则可以设置为流畅性好，若是调用海康的SDK进行二次开发，则可以调用接口[PlayM4_SetDisplayBuf](#sec_099)设置解码后缓冲为15个以内；

4.确定接口[PlayM4_SetStreamOpenMode](#sec_028)设定为STREAM_REALTIME；

5.确定网络良好，收发网络包延时较小。

# 流模式播放

## ``` Question 5 流模式下快放 ```

#### Answer 5

流模式下支持码流的快放，但是对当前送入数据的码流数据和网络环境是有要求的，比如若正常情况下，视频帧率为25帧的码流1倍速快放，若需要2倍速快放，
则需要的数据量是1倍速播放的2倍才能达到需求。

## ``` Question 6 流模式下倒放 ```

#### Answer 6

流模式下支持码流的倒放，支持本地录像文件以流模式送入数据倒放，若需要实现倒放则对送入数据是有要求的，必须送入的数据是一个GOP，且是逆序送入的数据。具体可以参考[PlayM4_ReversePlay](../接口定义/PlayM4_ReversePlay
.html)接口说明。

## ``` Question 7 实时流预览显示第一帧画面比较慢 ```

#### Answer 7

在低帧率下比较常见，检查第一帧是否I帧，若第一帧不是I帧则需要到I帧才能正常解码，所以时间可能比较长。

  
  
  

# 关于加密码流

## ``` Question 8 加密码流无法正常播放 ```

#### Answer 8

1.确认码流是否是基线的码流，若是定制的码流则需要联系分公司确认加密方式和订单号；

2.确认密钥和调用设置密钥接口被正确调用，且密钥正确[PlayM4_SetSecretKey](#sec_080)；

3.可以将码流发给我们确认。

  

# 关于抓图

## ``` Question 9 如何将捕获的图片保存在内存中以供后续处理 ```

#### Answer 9

在开始正常解码播放[PlayM4_Play](#sec_035)以后，可以通过播放库函数[PlayM4_GetBMP](#sec_117) 和[PlayM4_GetJPEG](#sec_118) 把图片保存在内存中。

## ``` Question 10 如何抓取每帧图像的BMP图片 ```

#### Answer 10

若需要抓图BMP图片，则需要调用[PlayM4_GetBMP](#sec_117)或者[PlayM4_ConvertToBmpFile](#sec_115);
其间区别是PlayM4_GetBMP接口在[PlayM4_Play](#sec_035)成功之后调用，但是不能在回调函数中调用此接口；PlayM4_ConvertToBmpFile接口可以在回调函数中调用，
生成BMP文件。使用需要注意申请保存BMP文件内存大小一般申请的内存大小图像宽*高*5，因RGB32数据是4倍的宽高，而bmp图像还有一个BMP文件头，因此简单起见这种方式分配内存，实际图像数据在pBmpSize返回，返回的数据直接写文件即可得到一幅bmp图像（RGB32)。

## ``` Question 11 如何抓取JPEG图片 ```

#### Answer 11

抓图JPEG图片可以调用，则需要调用[PlayM4_GetJPEG](#sec_118) 或者 [PlayM4_ConvertToJpegFile](#sec_116);
其间区别是 [PlayM4_GetJPEG](#sec_118) 接口在PlayM4_Play成功之后调用，但是不能在回调函数中调用此接口；PlayM4_ConvertToJpegFile接口可以在回调函数
中调用，生成JPEG文件。申请保存JPEG内存大小，建议申请的内存大小图像 宽*高*3/2，虽然jpeg压缩后小于这个设定的值，但是因可以设置jpeg图像质量，无法确定压缩比例。实际图像数据在pJpegSize
返回，返回的数据直接写文件即可得到一幅jpeg图像。

## ``` Question 12 如何保存每帧解码的视频图片 ```

#### Answer 12

1.成功解码显示状态下，可以通过 [PlayM4_SetDisplayCallBack](#sec_113) 回调函数中获取的每帧数据即为解码成功后送入到显卡做显示的数据，可以在回调函数中调用接口
 [PlayM4_ConvertToBmpFile](#sec_115) 或者 [PlayM4_ConvertToJpegFile](#sec_116) 接口保存图片。

2.若解码未显示，则可以调用PlayM4_Play接口此时，显示窗口句柄置为NULL，即可只解码不显示图像，此时可以调用解码回调函数 [PlayM4_SetDecCallBack](#sec_163) 接口获取解码后每帧数据。

  
  
  

# 关于播放声音问题

## ``` Question 13 音频播放卡顿，视频播放流畅 ```

#### Answer 13

确认音频数据是否均匀。

## ``` Question 14 复合流文件，播放音频时画面卡顿，不播放音频。则画面正常 ```

#### Answer 14

一般可能存在于低帧率文件，或者音频分布不均匀导致。

## ``` Question 15 播放文件，无法听到声音 ```

#### Answer 15

1.需要确定码流中是否有音频数据，音频源是有声音的。

2.音频封装相关表示类型的字段不符合规定，如RTP封装payload错误，PS封装stream type错误等。

3.音频未加密而在封装层为加密，在播放库6.2系列版本后开始关注音频加密字段。如果之前版本可以正常播放，之后版本不行，则可能是设备问题，需要和设备确认。

## ``` Question 16 关于PlayM4_Sound(Share)返回值的问题 ```

#### Answer 16

1.需要确定码流中是否有音频数据，若是纯视频码流，则该接口返回失败。

2.复合流中音频编码格式声明为0，则PlayM4_Sound返回失败，播放不了音频。

3.PlayM4_Sound必须在PlayM4_Play之后调用。

  
  
  

# 关于文件模式问题

## ``` Question 17 实时流播放正常，文件播放有快放现象 ```

#### Answer 17

确认码流中帧率或者时间戳是是否正常；另外可以检查是否有被抽帧的情况。

## ``` Question 18 文件打开失败 ```

#### Answer 18

检查保存文件时是否有保存正确的文件头（设备网络SDK的实时流回调函数中码流类型为NET_DVR_SYSHEAD，或者编码卡编码回调函数中当前帧类型为PktSysHeader）；文件是否小于4K或者大于4G；或者数据错误；或者没有关键帧（视频解码需要依赖于关键帧）。

## ``` Question 19 文件模式如何定位 ```

#### Answer 19

是否成功创建文件索引；若索引创建成功，检查设定的定位参数（如时间或者帧号）是否正确；

## ``` Question 20 PlayM4_SetCurrentFrameNum定位不准确 ```

#### Answer 20

是否成功创建文件索引；文件帧号是否乱序；

  
  
  
  

# 关于解码回调问题

## ``` Question 21 如何获取多路数据流解码后的数据 ```

#### Answer 21

1.一路数据对应一个播放库Port（通过[PlayM4_GetPort](#sec_022) 获取）;

2.调用[PlayM4_SetStreamOpenMode](#sec_028) 设定正确的播放模式；

3.送入这路数据对应的文件头[PlayM4_OpenStream](#sec_030);

4.调用[PlayM4_SetDecCallBack](#sec_163)注册解码回调函数，获取解码后的数据；

5. 调用[PlayM4_Play](#sec_035)开始解码线程（若不需要显示图像，则可以将窗口句柄置为NULL）;

6.调用[PlayM4_InputData](#sec_032) 送入每路数据正确的数据；播放库支持多路并发解码，当前版本最多支持500路。

## ``` Question 22 实时流数据用解码回调有丢帧现象 ```

#### Answer 22

1.实时录文件，先排除数据流是否有问题。

2.如果数据没有问题，注释掉解码回调里面所有的实现，查看是否还有丢帧情况。解码互调里面实现耗时比较多的操作，也有可能出现此类的问题。

3.请查看在实际调用过程中，检查 [PlayM4_InputData](#sec_032)是否有失败，若有失败，请尝试将数据重新送入，错误发生频率比较高，建议 [PlayM4_OpenStream](#sec_030)中设置缓冲区大小设置大一些。

## ``` Question 23 如何抓取RGB24数据 ```

#### Answer 23

海康播放库抓图接口生成的BMP图片都是RGB32格式的，若需要获取RGB24格式数据则建议用解码回调函数  [PlayM4_SetDecCallBack](#sec_163)，获取解码后的每一帧YV12格式数据，然后自行转码为RGB24格式即可；

## ``` Question 24 有些码流解码回调函数中获取的每帧视频高度只有显示原来的一半 ```

#### Answer 24

若原始图像分辨率是2CIF（PAL制为704*288，NTSC制为704*240），实际显示是按照PAL制704*576，NTSC制是704*480进行显示，而解码回调函数中获取的
是码流实际的视频分辨率，所以会出现这种情况。

## ``` Question 25 如何自己实现显示 ```

#### Answer 25

通过解码回调函数 [PlayM4_SetDecCallBack](#sec_163) 回调函数获取到解码后的视频和音频数据后，视频部分可以用windowsAPI中的strectchbilt实现，或者用Directshow中的Render部分实现；或者DirectDraw等方式实现；音频数据可以用windowsAPI函数实现。

## ``` Question 26 解码回调和抓图回调函数的区别 ```

#### Answer 26

[PlayM4_SetDecCallBack](#sec_163)解码以后就会将数据回调给用户，解码多少帧数据即回调多少帧，而  [PlayM4_SetDisplayCallBack](#sec_113)是将解码后的视频数据送入到显卡中显示的数据回调给用户。则是按照一个播放的帧率来回调的，比如帧率为25帧/s，回调的时候，就会间隔大概40ms回调一帧数据。

## ``` Question 27 解码回调函数中获取连续三帧音频数据时标信息重复 ```

#### Answer 27

这是播放库版本的问题，需要将播放库版本更新到最新版本。若需要得到准确的音频帧信息建议使用海康的码流分析库SDK。

  
  
  

# 关于同步回放问题

## ``` Question 28 如何实现多个文件的同步回放 ```

#### Answer 28

1.多个同步回放的文件必须有相同的时间戳片段;

2.在同步回放接口调用之前必须确认是否每个文件都有成功创建文档的索引；

3.同步回放的过程中可以通过定位接口 [PlayM4_SetPlayedTimeEx](#sec_065) 进行同步回放的定位。

  
  
  

# 关于智能码流的问题

## ``` Question 29 显示智能信息目标框闪烁 ```

#### Answer 30

1.可能是智能解析的目标框信息就有间隔性缺少的现象。

2.检查是否因时标问题导致部分智能信息未被同步上，如果是转封装的，排查SystemTransform.dll的问题，如果没有则是设备时标的问题，需要设备确认。

3.绘制过程中有问题。

  
  
  

# 关于智能码流的问题

## ``` Question 30 显示智能信息目标框闪烁 ```

#### Answer 31

1.可能是智能解析的目标框信息就有间隔性缺少的现象。

  
  
  

## ``` Question 31 智能码流显示规则线和目标框没有显示 ```

#### Answer 32

1.在播放库6.1.1.20之前的版本，不能解析新设备智能打包的码流，可以用新版本的播放库先测试确认一下。

2.非版本问题情况下，同上个问题的解答。

  
  
  

# 关于linux版本的播放库问题

## ``` Question 32 linux版本的播放库不能正常预览 ```

#### Answer 33

1.检查显卡驱动是否是最新版本，需要更新显卡驱动是最新版本；

2.检查OpenGL是否安装好，需要安装OpenGL;

3.检查是否是虚拟机，我们建议最好在真机上运行显示；

4.若依然不能显示则可以在海康官网上下载linux版本的播放器验证测试文件是否可以正常播放，若可以正常播放，则用户可以检查代码；若不能正常播放，则可能是码流问题。且可以确认码流是否是加密码流，若是加密码流则需要输入正确的密钥。

5.若可以显示但是画面比较卡顿，则检查驱动没有没有正确安装，当前linux版本播放库支持linux内核2.6以上版本。

  
  
  

# 关于Android版本的播放库问题

## ``` Question 33 Android版本的播放库不能正常预览 ```

#### Answer 34

1.海康anroid版本的播放库只支持真机，不支持虚拟机；

2.建议在文档中已经测试过的anroid版本中使用；

  
  
  

# 关于iOS版本的播放库问题

## ``` Question 34 iOS版本的播放库不能正常预览 ```

#### Answer 35

1.调用播放库PlayM4_Play接口在主线程调用；

2.模拟机和真机分别有对应版本，建议匹配使用；

3.Mac没有上述的限制，且Mac是动态库，ios是静态库，请配对使用；

---

<a id="sec_160"></a>
## 封面（附录）

**播放库****SDK**

**编程指南**

**V7.3.7**

<a id="sec_161"></a>
## PlayM4_GetPictureQuality（附录）

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_GetPictureQuality*

取图像质量。

```
int PlayM4_GetPictureQuality(
  int     nPort,
  int    *bHighQuality
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

*bHighQuality*
:   [out] 高质量，0表示低质量

#### Return Values

成功返回1；失败返回0。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

当前版本暂不支持此接口。

#### See Also

**[PlayM4_SetPicQuality](PlayM4_SetPicQuality.html)   [PlayM4_Play](PlayM4_Play.html)  

---**

<a id="sec_162"></a>
## PlayM4_GetTimerType（附录）

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_GetTimerType

获取播放使用的定时器类型。

```
int  PlayM4_GetTimerType(
  int              nPort,
  unsigned int*    pTimerType,
  unsigned int*    pReserved
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

*pTimerType*
:   [out] TIMER_1或TIMER_2

| **pTimerType参数** | 对应信息 |
| --- | --- |
| **TIMER_1** | 多媒体时钟，时间精度高； |
| **TIMER_2** | TIMER_2 是等待计时器，使用数目没有限制，但时间精度较低，不推荐在高倍速播放时使用。 |

*pReserved*
:   [out] 保留参数

#### Return Values

成功返回1；失败返回0。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

当前版本播放库已经按时间戳播放，没有16路高精度定时器的限制了。

当前版本暂不支持此接口

#### See Also

**[PlayM4_SetTimerType](PlayM4_SetTimerType.html)  

---**

<a id="sec_163"></a>
## PlayM4_SetDecCallBack（附录）

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_SetDecCallBack

解码回调。

```
int PlayM4_SetDecCallBack(
  int         nPort,
  DecCBFun    fDecCBFun
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

*fDecCBFun*
:   [in] 解码回调函数指针，若不需要调用回调函数则置为NULL，否则不能为NULL

#### Callback Function

```
typedef void(CALLBACK *DecCBFun)(
  int           nPort,
  char*         pBuf,
  int           nSize,
 FRAME_INFO*    pFrameInfo,
  int           nReserved1,
  int           nReserved2
);
```

#### Callback Function Parameters

*nPort*
:   [out] 播放器通道号

*pBuf*
:   [out] 解码后的音视频数据指针

*nSize*
:   [out] 解码后的音视频数据pBuf的长度

*pFrameInfo*
:   [out] 图像和声音信息结构体指针

*nReserved1*
:   [out] 保留参数

*nReserved2*
:   [out] 保留参数

#### Return Values

成功返回1；失败返回0。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

设置回调函数，替换播放器中的显示部分，由用户自己控制显示，该函数在PlayM4_Play之前调用，在PlayM4_Stop时自动失效，下次调用PlayM4_Play之前需要重新设置。  

解码部分不控制速度，只要用户从回调函数中返回，解码器就会解码下一部分数据。  

这个功能的使用需要用户对视频显示和声音播放有足够的了解，否则请慎重使用，有关知识请参阅directx开发包。  

当前解码的视频数据格式为YV12，音频解码格式为PCM。调用此回调函数后，则视频图像无显示。

建议不再使用此接口。

#### See Also

**[PlayM4_SetDecCallBackMend](PlayM4_SetDecCallBackMend.html)   [PlayM4_SetDisplayCallBack](PlayM4_SetDisplayCallBack.html)  

**[PlayM4_SetDecCBStream](PlayM4_SetDecCBStream.html)   [PlayM4_SetDecodeFrameType](PlayM4_SetDecodeFrameType.html)  

**[PlayM4_SetDecCallBackExMend](PlayM4_SetDecCallBackExMend.html)  

---******

<a id="sec_164"></a>
## PlayM4_SetDeflash（附录）

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_SetDeflash

去闪烁。

```
int PlayM4_SetDeflash(
  int    nPort,
  int    bDeflash
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

*bDeflash*
:   [in] 1表示设置去闪烁，0表示不设置，默认为不设置

#### Return Values

成功返回1；失败返回0。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

设置是否去闪烁功能, 原先在静止图像区域有噪声情况下, 图像会产生闪烁现象（或称刷新或跳动），启动去闪烁功能后，闪烁效果可消除或减轻，同时也能降低噪声。
此接口只在标准264下有效。

当前版本暂不支持此接口

#### See Also

**[PlayM4_SetColor](PlayM4_SetColor.html)   [PlayM4_GetColor](PlayM4_GetColor.html)  

**[PlayM4_SetImageSharpen](PlayM4_SetImageSharpen.html)

**[PlayM4_Play](PlayM4_Play.html)   [PlayM4_Stop](PlayM4_Stop.html)  

---******

<a id="sec_165"></a>
## PlayM4_SetPicQuality（附录）

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_SetPicQuality

设置图像质量。

```
int PlayM4_SetPicQuality(
  int    nPort,
  int    bHighQuality
);
```

#### Parameters

*nPort*
:   [in]
    播放通道号

*bHighQuality*
:   [in]
    等于1时图像高质量，等于0时低质量，默认为1

#### Return Values

成功返回1；失败返回0。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

- 当设置成高质量时画面效果好，但CPU利用率高。在支持多路播放时，可以设为低质量，以降低CPU利用率；当某路放大播放时将该路设置成高质量，以达到好的画面效果。
- 只有在有B帧的码流才有效，对于没有B帧的码流调用PlayM4_SetPictureQuality是无效果的。
- H265码流播放时，不支持调用该接口进行设置图像质量。

不再支持此接口。

#### See Also

**[PlayM4_GetPictureQuality](PlayM4_GetPictureQuality.html)   [PlayM4_Play](PlayM4_Play.html)  

---**

<a id="sec_166"></a>
## PlayM4_SetPlayMode（附录）

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_SetPlayMode*

设置播放模式。

```
int PlayM4_SetPlayMode(
  int    nPort,
  int    bNormal
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

*bNormal*
:   [in]是否正常播放

#### Return Values

成功返回1；失败返回0。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

当前版本暂不支持此接口。

#### See Also

**[PlayM4_Play](PlayM4_Play.html)   [PlayM4_Stop](PlayM4_Stop.html)  

---**

<a id="sec_167"></a>
## PlayM4_SetPreRecordCallBack（附录）

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_SetPreRecordCallBack

预录像数据回调函数。

```
int PlayM4_SetPreRecordCallBack(
  int               nPort,
  PreRecordCBfun    fPreRecordCBfun,
  void*             pUser
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

*fPreRecordCBfun*
:   [in] 预录像数据回调函数，若不需要调用回调函数则置为NULL，否则不能为NULL

#### Callback Function

```
typedef void(CALLBACK *PreRecordCBfun)(
  int                 nPort,
 RECORD_DATA_INFO    *pRecordDataInfo,
  void*               pUser
);
```

#### Callback Function Parameters

*nPort*
:   [out] 播放器通道号

*pRecordDataInfo*
:   [out] 预录像数据信息指针

*pUser*
:   [out] 用户指针

#### Return Values

成功返回1；失败返回0。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

- PlayM4_Play必须送入有效的显示窗口句柄。必须在正常显示第一帧视频数据后调用此接口才会成功。
- 回调出来的数据需要及时处理，不能阻塞回调函数，否则会造成录像丢帧。

不再支持此接口。

#### See Also

**[PlayM4_SetPreRecordFlag](PlayM4_SetPreRecordFlag.htm)  

---**

<a id="sec_168"></a>
## PlayM4_SetPreRecordFlag（附录）

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_SetPreRecordFlag

设置预录像开关。

```
int PlayM4_SetPreRecordFlag(
  int    nPort,
  int    bFlag
);
```

#### Parameters

*nPort*
:   [in]
    播放通道号

*bFlag*
:   [in]
    设置预录像开关，bFlag = 1表示开启，bFlag = 0表示关闭

#### Remarks

预录功能是把设备通过网络传输过来的码流转换为PS封装，然后通过回调函数中给用户，方便用户保存成文件查看。

不再支持此接口。

#### Return Values

成功返回1；失败返回0。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### See Also

**[PlayM4_SetPreRecordCallBack](PlayM4_SetPreRecordCallBack.html)  

---**

<a id="sec_169"></a>
## PlayM4_SetSycStartTime（附录）

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_SetSycStartTime*

设置同步回放开始时间。

```
int PlayM4_SetSycStartTime(
  int                  nPort,
 PLAYM4_SYSTEM_TIME   *pstSystemTime
);
```

#### Parameters

*nPort*
:   [in]
    播放通道号

*pstSystemTime*
:   [in]
    同步的系统时间结构体指针

#### Return Values

成功返回1；失败返回0。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

暂不支持此接口。

#### See Also

**[PlayM4_SetSycGroup](PlayM4_SetSycGroup.html)  

---**

<a id="sec_170"></a>
## PlayM4_SetTimerType（附录）

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_SetTimerType

设置播放使用的定时器类型。

```
int  PlayM4_SetTimerType(
  int             nPort,
  unsigned int    nTimerType,
  unsigned int    nReserved
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

*nTimerType*
:   [in] 时钟类型，如下表所示：

| **pTimerType参数** | 对应信息 |
| --- | --- |
| **TIMER_1** | 多媒体时钟，时间精度高； |
| **TIMER_2** | TIMER_2 是等待计时器，使用数目没有限制，但时间精度较低，不推荐在高倍速播放时使用。 |

*nReserved*
:   [in] 保留参数

#### Return Values

成功返回1；失败返回0。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

必须在PlayM4_OpenFile之前调用。建议在实时预览时设置成Timer2，在文件回放时设置为Timer1。若设置时钟失败则可能是系统资源不够导致。

当前版本暂不支持此接口

#### See Also

**[PlayM4_GetTimerType](PlayM4_GetTimerType.html)  

---**

<a id="sec_171"></a>
## PlayM4_SyncToAudio（附录）

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PlayM4_SyncToAudio*

设置音视频同步。

```
int PlayM4_SyncToAudio(
  int     nPort,
  int     bSyncToAudio
);
```

#### Parameters

*nPort*
:   [in] 播放通道号

*bSyncToAudio*
:   [in] 是否开启音视频同步

#### Return Values

成功返回1；失败返回0。获取错误码调用**[PlayM4_GetLastError](#sec_020)**。

#### Remarks

音视频同步需要以音视频的时间戳为基准，若时间戳有跳变，则可能会影响音视频同步的效果。

当前版本暂不支持。

#### See Also

**[PlayM4_PlaySound](PlayM4_PlaySound.html)   [PlayM4_StopSound](PlayM4_StopSound.html)  

---**

<a id="sec_172"></a>
## AdditionDataInfo（附录）

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# AdditionDataInfo

私有信息结构体。

```
struct{
  long      lDataType;
  long      lDataStrVersion;
  long      lDataTimeStamp;
  long      lDataLength;
  char    *pData;
}AdditionDataInfo;
```

#### Members

*lDataType*
:   私有数据类型

*lDataStrVersion*
:   数据返回的结构体版本，主要是为了兼容性

*lDataTimeStamp*
:   私有数据时间戳

*lDataLength*
:   私有数据长度

*pData*
:   私有数据指针

#### See Also

**[PlayM4_SetAdditionDataCallBack](../接口定义/PlayM4_SetAdditionDataCallBack.html)**

---

<a id="sec_173"></a>
## CROP_PIC_INFO（附录）

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# CROP_PIC_INFO

选择区域参数结构体。

```
struct{
  unsigned char    *pDataBuf;
  unsigned int     dwPicSize;
  unsigned int     dwBufSize;
  unsigned int     dwPicWidth;
  unsigned int     dwPicHeight;
  unsigned int     dwReserve;
  HKRECT          *pCropRect;
}CROP_PIC_INFO;
```

#### Members

*pDataBuf*
:   抓图数据buffer

*dwPicSize*
:   实际图片大小

*dwBufSize*
:   数据buffer大小

*dwPicWidth*
:   截图宽

*dwPicHeight*
:   截图高

*dwReserve*
:   多加一个reserve字段

*pCropRect*
:   选择区域NULL, 同老的抓图接口

#### Remarks

抓取出来的图片宽高是16的倍数，最小支持抓图分辨率为32 *32。

#### See Also

**[PlayM4_GetCropJPEG](../接口定义/PlayM4_GetCropJPEG.html)**

**[PlayM4_GetCropBMP](../接口定义/PlayM4_GetCropBMP.html)**

---

<a id="sec_174"></a>
## CYCLEPARAM（附录）

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# CYCLEPARAM

鱼眼图像圆心参数。

```
struct{
  float    fRadiusLeft;
  float    fRadiusRight;
  float    fRadiusTop;
  float    fRadiusBottom;
}CYCLEPARAM;
```

#### Members

*fRadiusLeft*
:   圆的最左边X坐标，取值范围为[0.0,1.0]

*fRadiusRight*
:   圆的最右边X坐标，取值范围为[0.0,1.0]

*fRadiusTop*
:   圆的最上边Y坐标，取值范围为[0.0,1.0]

*fRadiusBottom*
:   圆的最下边Y坐标，取值范围为[0.0,1.0]

#### See Also

**[PlayM4_FEC_SetParam](#sec_133)**

**[PlayM4_FEC_GetParam](#sec_134)**

---

<a id="sec_175"></a>
## D3D_PIC_INFO（附录）

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# D3D_PIC_INFO

d3d11渲染抓图结构体。

///=16。
unsigned int nPicHeight; //设置抓图高-nPicMode为1时有效，且高>=16。
unsigned char chReserve[8]; //reserve保留字段
}D3D_PIC_INFO;

```
struct{
  unsigned int    nPicMode;
  unsigned char    *pBuf;
  unsigned int    nBufSize;
  unsigned int*    pPicSize;
  unsigned int    nPicWidth;
  unsigned int    nPicHeight;
  unsigned char    chReserve[8];
}D3D_PIC_INFO;
```

#### Members

*nPicMode*
:   抓图模式：0-按照码流实际分辨率抓图(之前抓图模式)；1-按照下面传入的宽高抓图（nPicWidth*nPicHeight-窗口宽高或者其他宽高）

*pBuf*
:   抓图数据buffer

*nBufSize*
:   缓存buffer大小-（如果nPicMode为0则为之前的根据获取到的码流分辨率来进行缓存申请；如果nPicMode为1则上层根据设置的分辨率来申请缓存）

*pPicSize*
:   实际图片大小

*nPicWidth*
:   设置抓图宽-nPicMode为1时有效，且宽>=16

*nPicHeight*
:   设置抓图宽-nPicMode为1时有效，且宽>=16

*chReserve*
:   保留字节

#### See Also

**[PlayM4_GetD3DCapture](#sec_153)**

---

<a id="sec_176"></a>
## DISPLAY_INFO（附录）

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# DISPLAY_INFO

当前显示信息结构体。

```
struct{
  int      nPort;
  char    *pBuf;
  int      nBufLen;
  int      nWidth;
  int      nHeight;
  int      nStamp;
  int      nType;
  void*   nUser;
}DISPLAY_INFO;
```

#### Members

*nPort*
:   通道号

*pBuf*
:   返回图像数据指针

*nBufLen*
:   返回图像数据大小

*nWidth*
:   画面宽，单位像素

*nHeight*
:   画面高

*nStamp*
:   时标信息，单位毫秒

*nType*
:   数据类型，T_YV12，T_RGB32，T_UYVY

nType类型说明，如下表所示：

| nType宏定义 | nFrameType含义 |
| --- | --- |
| **T_AUDIO16** | 音频数据;采样率16khz，单声道，每个采样点16位表示,具体以解码出的音频信息为准 |
| **T_RGB32** | 视频数据。每个像素4个字节，排列方式与位图相似，“B-G-R-0 …”，第一个像素位于图像左下角,保留 |
| **T_UYVY** | 视频数据，uyvy格式。“U0-Y0-V0-Y1-U2-Y2-V2-Y3….”，第一个像素位于图像左上角,保留 |
| **T_YV12** | 视频数据，yv12格式,当前解码后的视频格式。排列顺序“Y0-Y1-……”，“V0-V1….”，“U0-U1-…..”。关于图像格式详细信息，用户可以查阅相关资料。 |

*nUser*
:   用户数据

#### Remarks

当前获取到的图像数据类型为YV12格式。

#### See Also

**[PlayM4_SetDisplayCallBackEx](#sec_114)  
[PlayM4_SetDecCallBack](#sec_163)**

---

<a id="sec_177"></a>
## ENCRYPT_INFO（附录）

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# ENCRYPT_INFO

加密信息结构体。

```
struct{
  long    nVideoEncryptType;
  long    nAudioEncryptType;
  long    nSetSecretKey;
}ENCRYPT_INFO;
```

#### Members

*nVideoEncryptType*
:   视频加密类型

*nAudioEncryptType*
:   音频加密类型

*nSetSecretKey*
:   是否设置，1表示设置密钥，0表示没有设置密钥

#### See Also

**[PlayM4_SetEncryptTypeCallBack](#sec_081)**

---

<a id="sec_178"></a>
## FECCOLOR（附录）

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# FECCOLOR

PTZ颜色。

```
struct{
  unsigned char    nR;
  unsigned char    nG;
  unsigned char    nB;
  unsigned char    nAlpha;
}FECCOLOR;
```

#### Members

*nR*
:   R分量

*nG*
:   G分量

*nB*
:   B分量

*nAlpha*
:   Alpha分量

#### Remarks

r,g,b,alpha都是从0-255有效值，alpha设置无效果。

#### See Also

**[PlayM4_FEC_SetParam](#sec_133)**

**[PlayM4_FEC_GetParam](#sec_134)**

---

<a id="sec_179"></a>
## FISHEYEPARAM（附录）

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# FISHEYEPARAM

鱼眼矫正参数结构体。

```
struct{
  unsigned int      nUpDateType;
  unsigned int      nPlaceAndCorrect;
  PTZPARAM          stPTZParam;
  CYCLEPARAM        stCycleParam;
  float             fZoom;
  float             fWideScanOffset;
  FECCOLOR          stPTZColor;
  int               nResver[15];
}FISHEYEPARAM;
```

#### Members

*nUpDateType*
:   更新的类型

*nPlaceAndCorrect*
:   安装方式和矫正方式（只能用于获取，SetParam的时候无效,该值表示安装方式和矫正方式的和）

*stPTZParam*
:   PTZ 校正的参数

*stCycleParam*
:   鱼眼图像圆心参数

*fZoom*
:   PTZ 显示的范围参数，取值范围：[0.00001f,1.0f]

*fWideScanOffset*
:   180或者360度校正的偏移角度

*stPTZColor*
:   PTZ颜色

*nResver*
:   保留字段

#### See Also

**[PlayM4_FEC_SetParam](#sec_133)**

**[PlayM4_FEC_GetParam](#sec_134)**

---

<a id="sec_180"></a>
## FRAME_INFO（附录）

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# FRAME_INFO

图像和声音信息结构体。

```
struct{
  int             nWidth;
  int             nHeight;
  int             nStamp;
  int             nType;
  int             nFrameRate;
  unsigned int    dwFrameNum;
}FRAME_INFO;
```

#### Members

*nWidth*
:   画面宽，单位像素。如果是音频数据则为音频声道数；

*nHeight*
:   画面高。如果是音频数据则为样位率；

*nStamp*
:   时标信息，单位毫秒

*nType*
:   数据类型，T_AUDIO16，T_RGB32， T_YV12。

nType类型说明，如下表所示：

| nType宏定义 | nFrameType含义 |
| --- | --- |
| **T_AUDIO16** | 音频数据;采样率16khz，单声道，每个采样点16位表示；具体以解码出的音频信息为准 |
| **T_RGB32** | 视频数据。每个像素4个字节，排列方式与位图相似，“B-G-R-0 …”，第一个像素位于图像左下角；保留 |
| **T_UYVY** | 视频数据，uyvy格式。“U0-Y0-V0-Y1-U2-Y2-V2-Y3….”，第一个像素位于图像左上角；保留 |
| **T_YV12** | 视频数据，yv12格式，当前解码后的视频格式。排列顺序“Y0-Y1-……”，“V0-V1….”，“U0-U1-…..”。关于图像格式详细信息，用户可以查阅相关资料。 |

*nFrameRate*
:   编码时产生的图像帧率，如果是音频数据则为采样率

*dwFrameNum*
:   帧号

#### See Also

**[PlayM4_SetDecCallBack](#sec_163)**

**[PlayM4_SetDecCallBackMend](#sec_073)**

**[PlayM4_SetDecCallBackExMend](#sec_074)**

---

<a id="sec_181"></a>
## FRAME_POS（附录）

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PFRAME_POS

查找到的关键帧的文件位置、帧序号、时标信息。

```
struct{
  long long  nFilePos;
  int          nFrameNum;
  int          nFrameTime;
  int          nErrorFrameNum;
SYSTEMTIME     *pErrorTime;
  int          nErrorLostFrameNum;
  int          nErrorFrameSize;
}FRAME_POS;
```

#### Members

*nFilePos*
:   文件位置

*nFrameNum*
:   帧序号

*nFrameTime*
:   帧时标（毫秒）

#### See Also

**[PlayM4_GetKeyFramePos](#sec_107)   [PlayM4_GetNextKeyFramePos](#sec_108)**

---

<a id="sec_182"></a>
## FRAME_TYPE（附录）

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# FRAME_TYPE

数据帧信息结构体。

```
struct{
  char    *pDataBuf;
  int      nSize;
  int      nFrameNum;
  int      bIsAudio;
  int      nReserved;
}FRAME_TYPE;
```

#### Members

*pDataBuf*
:   数据帧首地址

*nSize*
:   数据帧的大小

*nFrameNum*
:   数据帧的个数

*bIsAudio*
:   是否音频帧

*nReserved*
:   是保留

#### Remarks

不支持，相关功能可以使用其他库来实现。

#### See Also

**[PlayM4_GetSystemTime](#sec_061)**

**[PlayM4_SetSycStartTime](#sec_169)**

---

<a id="sec_183"></a>
## PLAYM4_SESSION_INFO（附录）

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PLAYM4_SESSION_INFO

交互信息结构。

```
struct{
  int               nSessionInfoType;
  int               nSessionInfoLen;
  unsigned char    *pSessionInfoData;
}PLAYM4_SESSION_INFO;
```

#### Members

*nSessionInfoType*
:   交互信息类型，不同的协议类型(nProtocolType)对应不同的交互信息

    | **nProtocolType** | **nSessionInfoType** | 宏定义值 | 含义 |
    | --- | --- | --- | --- |
    | **PLAYM4_PROTOCOL_RTSP** | **PLAYM4_SESSION_INFO_SDP** | 1 | RTSP协议交互的SDP信息 |

*nSessionInfoLen*
:   交互信息长度

*pSessionInfoData*
:   交互信息数据指针

#### See Also

**[PlayM4_OpenStreamAdvanced](#sec_033)**

---

<a id="sec_184"></a>
## PLAYM4_SYSTEM_TIME（附录）

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PLAYM4_SYSTEM_TIME

全局时间结构体。

```
struct{
  unsigned int    dwYear;
  unsigned int    dwMon;
  unsigned int    dwDay;
  unsigned int    dwHour;
  unsigned int    dwMin;
  unsigned int    dwSec;
  unsigned int    dwMs;
}PLAYM4_SYSTEM_TIME;
```

#### Members

*dwYear*
:   年

*dwMon*
:   月

*dwDay*
:   日

*dwHour*
:   时

*dwMin*
:   分

*dwSec*
:   秒

*dwMs*
:   毫秒

#### Remarks

获取当前播放帧对应的全局时间。

#### See Also

**[PlayM4_GetSystemTime](#sec_061)**

**[PlayM4_SetSycStartTIme](#sec_169)**

---

<a id="sec_185"></a>
## PTZPARAM（附录）

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# PTZPARAM

PTZ 校正的参数结构体。

```
struct{
  float      fPTZPositionX;
  float      fPTZPositionY;
}PTZPARAM;
```

#### Members

*fPTZPositionX*
:   PTZ 显示的中心位置 X坐标

*fPTZPositionY*
:   PTZ 显示的中心位置 Y坐标

#### Remarks

若鱼眼安装模式为FEC_PLACE_FLOOR 和FEC_PLACE_CEILING，坐标（fPTZPositionX，fPTZPositionY)到(0.5,0.5)的距离需要小于等于0.4，否则设置无效。  
若鱼眼安装模式为FEC_PLACE_WALL模式，则必须满足：  
(fPositionY - 0.5f)*(fPTZPositionY- 0.5f) + (fPTZPositionX- 0.5f)*(fPTZPositionX- 0.5f)
<= 0.16  
若令:  
zeta = asin((fPTZPositionY- 0.5f) / 0.5f); //直角坐标系Y坐标转垂直角度   
zcos = cos(zeta)；  
zsin = sin(zeta);  
必须满足((fPTZPositionX- 0.5f) / 0.5f / zcos)<= 1 且 ((fPTZPositionX- 0.5f) / 0.5f / zcos))>= -1  
否则设置无效。

设置的鱼眼矫正区域，处于很边缘的地方，PTZ校正设置也会失效。处于很边缘的地方指的是：一个圆（鱼眼镜头），画一个外切正方形，在正方形内、圆外（包括圆边界）的4个角、4个边。

#### See Also

**[PlayM4_FEC_SetParam](#sec_133)**

**[PlayM4_FEC_GetParam](#sec_134)**

---

<a id="sec_186"></a>
## RECORD_DATA_INFO（附录）

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# RECORD_DATA_INFO

预录像数据信息结构体。

```
struct{
  int                nType;
  int                nStamp;
  int                nFrameNum;
  int                nBufLen;
  char*              pBuf;
 PLAYM4_SYSTEM_TIME  stSysTime,
}RECORD_DATA_INFO;
```

#### Members

*nType*
:   数据类型，如文件头，视频，音频，私有数据等；

*nStamp*
:   时间戳；

*nFrameNum*
:   帧号

*nBufLen*
:   数据长度

*pBuf*
:   帧数据，以帧为单位回调

*stSysTime*
:   全局时间

#### See Also

**[PlayM4_SetPreRecordCallBack](#sec_167)**

---

<a id="sec_187"></a>
## SYSTEMTIME（附录）

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# SYSTEMTIME

系统时间结构体。

```
struct{
  short      wYear;
  short      wMonth;
  short      wDayOfWeek;
  short      wDay;
  short      wHour;
  short      wMinute;
  short      wSecond;
  short      wMilliseconds;
}SYSTEMTIME;
```

#### Members

*wYear*
:   年

*wMonth*
:   月

*wDayOfWeek*
:   星期

*wDay*
:   日

*wHour*
:   时

*wMinute*
:   分

*wSecond*
:   秒

*wMilliseconds*
:   毫秒

#### See Also

**[FRAME_POS](#sec_181)**

---

<a id="sec_188"></a>
## WATERMARK_INFO（附录）

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# WATERMARK_INFO

水印信息结构体。

```
struct{
  char    *pDataBuf;
  int      nSize;
  int      nFrameNum;
  int      bRsaRight;
  int      nReserved;
}WATERMARK_INFO;
```

#### Members

*pDataBuf*
:   水印数据指针

*nSize*
:   水印数据大小

*nFrameNum*
:   当前帧号

*bRsaRight*
:   是否是RSA加密（暂时作为保留参数）

*nReserved*
:   保留

#### See Also

**[PlayM4_SetCheckWatermarkCallBack](#sec_079)**

---

<a id="sec_189"></a>
## 预录模块流程（附录）

|  |
| --- |
|  |

|  |
| --- |
| 播放库SDK编程指南 |

# 预录模块流程

![](images/预录模块流程图.JPG)

  
  

预录功能模块是把设备通过网络传输过来的码流转换为PS封装，然后通过回调函数给用户，方便用户保存为本地文件查看。  
  

- 设置预录开关：设置预录开关标志位，调用的接口[PlayM4_SetPreRecordFlag](#sec_168)。
- 设置预录数据回调函数：调用的接口有[PlayM4_SetPreRecordCallBack](#sec_167)。

#### 示例代码

示例：预录模块流程

```

#include <stdio.h>
#include <iostream>
#include "SynPlayMode.h"
#include "SynPlayModeDlg.h"
#include "PlayM4.h"
#include "HCNetSDK.h"
#include "unistd.h"
using namespace std;

HWND hWnd = 0;  //Linux系统如果使用Qt进行界面开发，可以获取窗口句柄

//预录数据保存的本地文件
HANDLE g_hVidPreFile = CreateFile("Prereord.mp4",GENERIC_WRITE,FILE_SHARE_WRITE,NULL,CREATE_ALWAYS,FILE_ATTRIBUTE_NORMAL,NULL);

//预录回调函数
void CALLBACK fPreRecordCBfun(long nPort, RECORD_DATA_INFO *pRecordDataInfo,void* pUser)
{
	DWORD dwSize = 0;
	if (pRecordDataInfo == NULL)
	{
		return;
	}
	if (pRecordDataInfo->nType)
	{
		if (g_hVidPreFile != NULL)
		{
			WriteFile(g_hVidPreFile,pRecordDataInfo->pBuf,pRecordDataInfo->nBufLen,&dwSize,NULL);
		}
		
	}
}


BOOL g_bDecFlag = FALSE;
//解码回调函数
void CALLBACK DecCBFun(long nPort,char * pBuf,long nSize,
					   FRAME_INFO * pFrameInfo, 
					   long nReserved1,long /*nReserved2*/)
{

	CPlayerDlg* pDlg = (CPlayerDlg *)nReserved1;
	DWORD dwSize = 0;
	if (pFrameInfo->nType == T_AUDIO16)
	{
		OutputDebugString("Zytest:: get audio data !\n");
		WriteFile(g_hAudFile,pBuf,nSize,&dwSize,NULL);
	}
	else if ( pFrameInfo->nType == T_YV12 ) 
	{   
        //成功解码出第一帧数据，设置标记位置
		g_bDecFlag = TRUE;
      }
 }


long lPort = -1;
BOOL g_bFlag = FALSE;

//网络SDK的实时流回调函数
void CALLBACK fRealDataCallBack_V30(LONG lRealHandle, DWORD dwDataType, BYTE *pBuffer, DWORD dwBufSize, void* pUser)
{
	BOOL bFlag =  TRUE;
    CPlayerDlg* pDlg = (CPlayerDlg*)pUser;

	switch (dwDataType)
	{
	case NET_DVR_SYSHEAD://当前类型为文件头
       //获取当前播放库端口
		bFlag = PlayM4_GetPort(&lPort);
        //设置实时流打开模式
		bFlag = PlayM4_SetStreamOpenMode(lPort,1);	
        //打开实时流数据	
		bFlag = PlayM4_OpenStream(lPort,pBuffer,dwBufSize,4*1024*1024);
        //设置预录标记
		bFlag = PlayM4_SetPreRecordFlag(lPort,TRUE);
        //设置解码回调，此处用来确认是否有成功解码出第一帧数据
		bFlag = PlayM4_SetDecCallBackExMend(lPort,DecCBFun,NULL,0,NULL);
	    //开始解码，此处的显示窗口必须为有效的句柄，否则预录回调函数不能设置成功
		bFlag = PlayM4_Play(lPort,hWnd);
		break;
	case NET_DVR_STREAMDATA:
        //送入待解码的数据
		bFlag = PlayM4_InputData(lPort,pBuffer,dwBufSize);

	    //若未成功设置过预录数据回调函数，且成功解码出第一帧数据，则设置预录数据回调函数
		if ((g_bFlag== FALSE)&&(g_bDecFlag == TRUE))
		{
			Sleep(100);
			OutputDebugString("zytest:: set dec callback success !");
			//设置预录数据回调函数
            g_bFlag = PlayM4_SetPreRecordCallBack(lPort,fPreRecordCBfun,pUser);
			if (g_bFlag == FALSE)
			{
				DWORD dwErr = PlayM4_GetLastError(lPort);	
			}
			else
			{
				OutputDebugString("zytest:: set pre record callback success !");
			}
		}
		break;

	}

}


//get stream from the device
void main()
{
	BOOL bFlag = TRUE;
	NET_DVR_DEVICEINFO_V30 strDeviceInfo = {0};
	LONG lUserId = -1;
	DWORD dwErr = 0;
	NET_DVR_Init();

    //设备登录
	lUserId = NET_DVR_Login_V30("10.16.2.248",8000,"admin","12345",&strDeviceInfo);
	if (lUserId == -1)
	{
		dwErr = NET_DVR_GetLastError();
		AfxMessageBox("The device is not on line!");
		return FALSE;
	} 

	NET_DVR_CLIENTINFO strClientInfo = {0};
	strClientInfo.hPlayWnd           = 0;
	strClientInfo.lChannel           = 1;
	strClientInfo.lLinkMode          = 0;
	strClientInfo.sMultiCastIP       = NULL;
    //注册实时流回调函数
	LONG lRealHandle = NET_DVR_RealPlay_V30(lUserId,&strClientInfo,fRealDataCallBack_V30,(void*)(this),FALSE);
	if (lRealHandle == -1)
	{
		dwErr = NET_DVR_GetLastError();
		AfxMessageBox("The device do not get stream!");
		return FALSE;
	}

	Sleep(60000);

    NET_DVR_StopRealPlay(lRealHandle);
    lRealHandle = -1;

    if (lPort != -1)
    {
        PlayM4_Stop(lPort);
        PlayM4_CloseStream(lPort);
        PlayM4_FreePort(lPort);
        lPort = -1;
    }
    NET_DVR_Logout(lUserId);
    lUserId = -1;
    NET_DVR_CleanUp();
}



```

  

---
