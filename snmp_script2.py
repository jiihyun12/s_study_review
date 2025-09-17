import time
ip = "192.168.1.1"
#oid_in = ".1.3.6.1.2.1.2.2.1.10.9"   # ifHCInOctets.2 (예시: 포트2)
#oid_out = ".1.3.6.1.2.1.2.2.1.16.9" # ifHCOutOctets.2
oid_in  = ".1.3.6.1.2.1.31.1.1.1.6.9"   # ifHCInOctets.9 (64bit)
oid_out = ".1.3.6.1.2.1.31.1.1.1.10.9"  # ifHCOutOctets.9
to = "2000"
tr = "1"

# 캐시 준비 (전역 딕셔너리)
if not hasattr(system.util, "__bps_cache__"):
   system.util.__bps_cache__ = {}

# 현재값 읽기
# 1차 측정
v1_in = int(system.snmp.get(ip,161,[oid_in],"public",to, tr)[0])
v1_out = int(system.snmp.get(ip,161,[oid_out],"public",to, tr)[0])
t1 = time.time()

time.sleep(5)  # 5초 간격

# 2차 측정
v2_in = int(system.snmp.get(ip,161,[oid_in],"public",to, tr)[0])
v2_out = int(system.snmp.get(ip,161,[oid_out],"public",to, tr)[0])
t2 = time.time()

# 계산
dt = t2 - t1
bps_in = (v2_in - v1_in) * 8 / dt
bps_out = (v2_out - v1_out) * 8 / dt
