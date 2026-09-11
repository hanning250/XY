using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.IO;

namespace TrafficDemo.Common
{
    class CommonMethod
    {
        static string sCurPath = AppDomain.CurrentDomain.BaseDirectory;

        public static string ReadConfigValue(string filePath, string key)
        {
            // 确保文件存在
            if (!File.Exists(filePath))
            {
                throw new FileNotFoundException("配置文件未找到。", filePath);
            }

            // 读取文件内容
            string[] lines = File.ReadAllLines(filePath);

            foreach (string line in lines)
            {
                // 忽略注释行
                if (line.StartsWith("#"))
                    continue;

                // 按等号分割键和值
                string[] keyValue = line.Split(new char[] { '=' }, 2);
                if (keyValue.Length == 2 && keyValue[0].Trim() == key)
                {
                    return keyValue[1].Trim();
                }
            }

            // 如果没有找到指定的键，抛出异常或返回null
            throw new KeyNotFoundException("在配置文件中未找到指定的键：" + key);
        }

        public static string SaveFilePath(string fileName, string postFix, string folderName)//返回文件路径,保存在当前目标平台(x64/x86)/outputFiles/folderName路径下
        {
            var format = "yyyyMMdd_HHmmss_FFF";
            string folder = Path.Combine(sCurPath, "outputFiles", folderName);

            if (false == System.IO.Directory.Exists(folder))
            {
                System.IO.Directory.CreateDirectory(folder);
            }

            string filePath = Path.Combine(folder, fileName + "_" + DateTime.Now.ToString(format) + postFix);
            return filePath;
        }
    }
}
