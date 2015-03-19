WEBMIN_FW_TCP_INCOMING = 22 80 443 9418 12320 12321

COMMON_OVERLAYS = nginx

include $(FAB_PATH)/common/mk/turnkey/mysql.mk
include $(FAB_PATH)/common/mk/turnkey.mk
