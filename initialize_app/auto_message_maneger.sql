/*
 Navicat Premium Data Transfer
 Source Server Type    : MySQL
 Source Schema         : auto_message_maneger

 Target Server Type    : MySQL
 File Encoding         : 65001
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

DROP DATABASE IF EXISTS auto_message_maneger;
CREATE DATABASE auto_message_maneger;
USE auto_message_maneger;

-- ----------------------------
-- Table structure for access_log
-- ----------------------------
DROP TABLE IF EXISTS `access_log`;
CREATE TABLE `access_log`  (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `route` varchar(255) CHARACTER SET utf8mb4 NOT NULL,
  `host` varchar(45) CHARACTER SET utf8mb4 NOT NULL,
  `ip` varchar(45) CHARACTER SET utf8mb4 NOT NULL,
  `dt` datetime(0) NOT NULL DEFAULT CURRENT_TIMESTAMP(0),
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 543 CHARACTER SET = utf8mb4 ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for err_logs
-- ----------------------------
DROP TABLE IF EXISTS `err_logs`;
CREATE TABLE `err_logs`  (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `err_time` datetime(0) NOT NULL DEFAULT CURRENT_TIMESTAMP(0),
  `repr` varchar(1024) CHARACTER SET utf8mb4 NOT NULL,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 69 CHARACTER SET = utf8mb4 ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for local_post_logs
-- ----------------------------
DROP TABLE IF EXISTS `local_post_logs`;
CREATE TABLE `local_post_logs`  (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `computer` varchar(255) CHARACTER SET utf8mb4 NOT NULL,
  `report_id` int(11) NOT NULL,
  `report_name` varchar(255) CHARACTER SET utf8mb4 NOT NULL,
  `is_empty` tinyint(4) NOT NULL,
  `dt` datetime(0) NOT NULL DEFAULT CURRENT_TIMESTAMP(0),
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 1 CHARACTER SET = utf8mb4 ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for post_logs
-- ----------------------------
DROP TABLE IF EXISTS `post_logs`;
CREATE TABLE `post_logs`  (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `report_id` int(11) NOT NULL,
  `dt` datetime(0) NOT NULL DEFAULT CURRENT_TIMESTAMP(0),
  `trigger` varchar(45) CHARACTER SET utf8mb4 NOT NULL DEFAULT 'sys',
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 1884 CHARACTER SET = utf8mb4 ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for reports
-- ----------------------------
DROP TABLE IF EXISTS `reports`;
CREATE TABLE `reports`  (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(255) CHARACTER SET utf8mb4 NOT NULL COMMENT '报表在管理界面显示的名称',
  `post_time` int(11) NOT NULL COMMENT '报表发送的时间, 值为超过 00:00 的秒数',
  `post_weekday` varchar(45) CHARACTER SET utf8mb4 NOT NULL DEFAULT '',
  `post_day` varchar(45) CHARACTER SET utf8mb4 NOT NULL DEFAULT '',
  `receiver` varchar(1024) CHARACTER SET utf8mb4 NOT NULL,
  `builder_name` varchar(255) CHARACTER SET utf8mb4 NOT NULL COMMENT '调用的报告生成器的名称, 用于索引具体的类',
  `info` json NOT NULL COMMENT '初始化报表生成器所需要的信息',
  `complete_time` int(11) NULL DEFAULT NULL COMMENT '邮件发送的时间, 如果未发送则为 null',
  `remarks` varchar(1024) CHARACTER SET utf8mb4 NOT NULL,
  `delete_time` datetime(0) NULL DEFAULT NULL,
  `creator` varchar(45) CHARACTER SET utf8mb4 NOT NULL DEFAULT '',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `id_UNIQUE`(`id`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 178 CHARACTER SET = utf8mb4 ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for robot_err_logs
-- ----------------------------
DROP TABLE IF EXISTS `robot_err_logs`;
CREATE TABLE `robot_err_logs`  (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `err_time` datetime(0) NOT NULL DEFAULT CURRENT_TIMESTAMP(0),
  `repr` varchar(1024) CHARACTER SET utf8mb4 NOT NULL,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 74 CHARACTER SET = utf8mb4 ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for robot_said
-- ----------------------------
DROP TABLE IF EXISTS `robot_said`;
CREATE TABLE `robot_said`  (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `robot` varchar(255) CHARACTER SET utf8mb4 NOT NULL,
  `task_id` int(11) NOT NULL,
  `dt` datetime(0) NOT NULL DEFAULT CURRENT_TIMESTAMP(0),
  `said` mediumtext CHARACTER SET utf8mb4 NOT NULL,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 1658 CHARACTER SET = utf8mb4 ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for robot_tasks
-- ----------------------------
DROP TABLE IF EXISTS `robot_tasks`;
CREATE TABLE `robot_tasks`  (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `task` json NOT NULL,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 64 CHARACTER SET = utf8mb4 ROW_FORMAT = Dynamic;

-- ----------------------------
-- Event structure for reset_complete_time
-- ----------------------------
DROP EVENT IF EXISTS `reset_complete_time`;
delimiter ;;
CREATE EVENT `reset_complete_time`
ON SCHEDULE
EVERY '1' DAY STARTS '2020-02-21 00:00:00'
ON COMPLETION PRESERVE
DO update reports set complete_time = null
;;
delimiter ;

SET FOREIGN_KEY_CHECKS = 1;
