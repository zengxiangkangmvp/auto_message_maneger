## 自动通知管理器

### 服务需求相关背景

​	针对数据分析报表频繁手动分发问题，设计使用SQL构造数据分析报表同时设置触发条件的自动分发程序。

### 服务配置流程

1. 数据库文件：在MySQL数据库服务运行initialize_app文件夹下的auto_message_maneger.sql文件。
2. 配置JSON文件：将initialize_app文件夹下的auto_message_maneger文件夹放置USERPROFILE/Documents/的路径下，逐个完善以下JSON文件，其中dbs.json和mails.json为必要完善信息，robots.json可在前端页面设置。
    - dbs.json：设置MySQL数据库连接配置信息。
    - mails.json：设置自动发送邮件服务的邮箱相关信息。
    - robots.json ： 设置钉钉邮箱的群机器人相关信息。

### 功能简介

- 邮箱自动通知：共5类数据分析报表模板，根据不同的需求选择合适的分析报表模板；测试成功后再设置定时触发（使用场景：正式分析报表）。
- 钉钉群机器人：共3类数据分析报表模板，根据不同的需求选择合适的分析报表模板；测试成功后再设置定时触发（使用场景：非正式分析报表）。