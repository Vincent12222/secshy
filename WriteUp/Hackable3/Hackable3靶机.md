# Hackable3靶机

## 信息搜集

1. 使用`arp-scan -l`扫描网段下存活的ip，找到目标靶机的ip地址。

![image-20251120145224079](D:\漏洞复现\Hackeable3\assets\image-20251120145224079.png)

2. 用nmap扫描目标靶机开放的端口,目标开放了22端口和80端口。

   ```
   nmap -p- 192.168.1.10
   ```

   

![image-20251120150142684](assets/image-20251120150142684.png)

3. 访问80端口进入主页，查看源代码发现提示。得到登录页面地址和用户。

![image-20251120150604999](assets/image-20251120150604999.png)

![image-20251120150752259](assets/image-20251120150752259.png)

```
Please, jubiscleudo, don't forget to activate the port knocking when exiting your section, and tell the boss not to forget to approve the .jpg file - dev_suport@hackable3.com" 
```

4. 使用dirsearch工具扫描目录

   ```
   dirsearch -u http://192.168.1.10/ -i 200
   ```

   ![image-20251120151606036](assets/image-20251120151606036.png)

5. 访问/config页面，查看1.txt文件。得到一串base64编码。

![image-20251120151824142](assets/image-20251120151824142.png)

![image-20251120151909006](assets/image-20251120151909006.png)

6. 在[Base64编码解码](https://base64.us/)这个网站进行解码，得到敲门端口**10000**

![image-20251120152301251](assets/image-20251120152301251.png)

7. 访问login.php,查看源码。查看3.jpg。

![image-20251120152721320](assets/image-20251120152721320.png)

![image-20251120152823274](assets/image-20251120152823274.png)

8. 将图片下载到本地

   ```
   wget http://192.168.1.10/3.jpg
   ```

   ![image-20251120153004411](assets/image-20251120153004411.png)

9. 使用steghide工具查看图片是否存在隐写,查看结果文件发现**65535**端口

   ```
   steghide extract -sf 3.jpg
   ```

   ![image-20251120153333116](assets/image-20251120153333116.png)

10. 访问css目录发现存在2.txt文件，点击查看得到一串BrainFuck编码。

![image-20251120153746581](assets/image-20251120153746581.png)

![image-20251120153808693](assets/image-20251120153808693.png)

11. 在[Brainfuck/OoK加密解密 - Bugku CTF平台](https://ctf.bugku.com/tool/brainfuck/)进行解码。得到**4444**端口

![image-20251120154156498](assets/image-20251120154156498.png)

12. 访问backup目录查看wordlist.txt文件，发现很多密码。将文件下载到本地

![image-20251120154343371](assets/image-20251120154343371.png)

```
wget http://192.168.1.10/backup/wordlist.txt
```

![image-20251120154948474](assets/image-20251120154948474.png)

13. 

