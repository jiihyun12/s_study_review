# 2509

import os
import time
import re

def getPort(DeviceList=None, Name=None):
    """
    DeviceList: { AssetID: [IP, Category], ... } 형태의 딕셔너리
    Name: 수집할 항목 이름 ("Status" | "BpsIn" | "BpsOut")
          - "Status": ifOperStatus.X (포트 Up/Down)
          - "BpsIn":  ifInOctets.X   (누적 바이트, 32bit)  ← 실제 bps가 아니라 '누적'값
          - "BpsOut": ifOutOctets.X  (누적 바이트, 32bit)
    반환: [{AssetID: [SNMP응답문자열들...]}, ...] 리스트
    """

    if DeviceList is None:
        DeviceList = {}

    results = []  # 각 장비별 수집 결과를 담아 반환할 리스트

    # 포트별로 조회할 기준 OID 베이스 (끝에 ifIndex가 붙음)
    baseOid = {
        "Status" : ".1.3.6.1.2.1.2.2.1.8.",   # ifOperStatus.X
        "BpsIn"  : ".1.3.6.1.2.1.2.2.1.10.",  # ifInOctets.X (32bit 누적)
        "BpsOut" : ".1.3.6.1.2.1.2.2.1.16."   # ifOutOctets.X (32bit 누적)
    }

    # 장비 하나씩 순회
    for id, val in DeviceList.items():
        IP  = val[0]  # 장비 IP
        cat = val[1]  # 장비 카테고리 (예: "Network" 등, 필요 시 조건 분기 가능)

        portCount = 24   # 이번 수집 대상으로 보는 포트 개수(1~24)
        startIndex = 1   # ifIndex가 1부터 24까지 '직접' 대응된다는 가정 (주의! 장비마다 다름)

        # 조회할 OID 배열(예: '.1.3.6.1... .8.1' ~ '.1.3.6.1... .8.24')
        OID = [baseOid[Name] + str(startIndex + i - 1) for i in range(1, portCount + 1)]

        # SNMP getBulk 호출
        #  - 0: non-repeaters
        #  - portCount: max-repetitions (24개 정도면 한 번에 받기 위함)
        #  - 'public': 커뮤니티
        #  - "1000": timeout(ms)  ← 문자열이지만 보통 정수를 권장(2000 등)
        #  - "1": retries         ← 이 역시 정수 권장
        snmp_result = system.snmp.getBulk(IP, 161, OID, 0, portCount, 'public', "1000", "1")

        # 에러 문자열 형태로 돌아오는 경우를 방어
        if (snmp_result and isinstance(snmp_result, list)
                and isinstance(snmp_result[0], basestring)
                and snmp_result[0].startswith('Error:')):
            # 이 장비는 건너뜀
            continue

        # 정상 결과를 {AssetID: 결과리스트} 형태로 누적
        results.append({id: snmp_result})

    return results


def getAssetList(Group=''):
    """
    특정 DeviceGroup에 속한 장비들을 DB에서 가져와
    {AssetID: [IP, Category]} 딕셔너리로 반환.
    - 네임드 쿼리 'NetworkAssets' 가 존재해야 하며,
      파라미터 {"assetID":0,"deviceGroup":Group}를 받아
      AssetID, IPAddress, AssetCategory 컬럼을 반환해야 함.
    """
    AssetList = system.db.runNamedQuery('NetworkAssets', {"assetID": 0, "deviceGroup": Group})

    DeviceList = {}
    for row in AssetList:
        AssetID = row['AssetID']
        IP = row['IPAddress']
        cat = row['AssetCategory']
        DeviceList[AssetID] = [IP, cat]

    return DeviceList


def setAssetList(Group='', Name=None):
    """
    1) Group에 해당하는 장비 목록 조회
    2) getPort()로 SNMP 결과 수집
    3) 결과를 파싱해 NetworkAssets 테이블의 포트별 컬럼(P{n}{Name}) 갱신
       - 예: Name='Status' → P1Status, P2Status, ...
       - 예: Name='BpsIn'  → P1BpsIn, P2BpsIn,  ...
       - 예: Name='BpsOut' → P1BpsOut, ...
    주의:
      - 현재 BpsIn/BpsOut은 '누적 바이트'를 그대로 넣는 구조.
        실제 bps를 원하면 Δ(두 시점 차) 기반 계산 로직이 별도로 필요.
      - ifIndex가 1..24가 아닐 수 있음(장비마다 1000001부터 시작 등). 이 경우 매핑이 필요.
    """
    DeviceList = getAssetList(Group)

    # SNMP 결과 수집
    snmp_results = getPort(DeviceList, Name)

    # 장비별로 결과를 꺼냄
    for device in snmp_results:
        for id, statuses in device.items():
            # UPDATE SET 절을 동적으로 구성할 키-값 쌍 문자열 배열
            pairs = []

            # ---- 응답을 dict로 정리 (ifIndex -> 값) ----
            # statuses 항목 예시: ["1.3.6.1...= 2", "1.3.6.1...= 1", ...]
            vals = {}
            for r in statuses:
                s = str(r)
                parts = s.split('=')
                if len(parts) == 2:
                    # 왼쪽: "OID", 오른쪽: "값"
                    try:
                        idx = int(parts[0].split('.')[-1].strip())   # OID 마지막이 ifIndex
                    except:
                        continue
                    try:
                        val = int(parts[1].strip())                  # 값(정수화 시도)
                    except:
                        # 숫자로 변환 불가하면 스킵
                        continue
                    vals[idx] = val

            # ---- dict에서 꺼내서 SQL SET 구문 생성 ----
            # 현재는 ifIndex가 '1..24'라고 가정해 P1..P24 매핑
            # (장비가 1000001부터 시작하면 전부 NULL 들어갈 수 있음)
            for i in range(1, 25):
                v = vals.get(i)
                if v is None:
                    # 값이 없으면 NULL로
                    pairs.append("P{}{} = NULL".format(i, Name))
                else:
                    # 값이 있으면 해당 값으로
                    pairs.append("P{}{} = {}".format(i, Name, v))

            setStatus = ", ".join(pairs)

            # 최종 UPDATE 쿼리 구성
            query = """
                UPDATE NetworkAssets
                SET {}
                WHERE AssetID = ?
            """.format(setStatus)

            params = [id]

            # DB 업데이트 실행 (DITTO_DCIM 커넥션 사용)
            rows = system.db.runPrepUpdate(query, params, 'DITTO_DCIM')
            print "updated rows:", rows, "AssetID:", id


def portAlarm():
    """
    Audit 테이블에서 위험 상태(NewValue IN (2,3) 가정)를 조회해
    사용자에게 알림을 띄움.
    주의:
      - system.gui.messageBox는 Vision 클라이언트/디자이너에서만 사용 가능.
        게이트웨이 스크립트에선 동작하지 않음.
      - 게이트웨이에서 경보를 내보내려면 알람 파이프라인 또는
        Perspective 메시지/노티(모바일, 이메일 등)로 전환 권장.
    """
    database_name = 'DITTO_DCIM'
    query = """
        SELECT AssetID, ColumnName, NewValue, ModifiedDate
        FROM NetworkAssetsAudit
        WHERE NewValue IN (2, 3);
        -- AND ModifiedDate >= DATEADD(MINUTE, -10, GETDATE());  # 최근 10분 제한 예시 (MSSQL)
    """

    results = system.db.runPrepQuery(query, [], database_name)
    print(results)

    if results:
        for row in results:
            asset_id = row["AssetID"]
            column_name = row["ColumnName"]
            new_value = row["NewValue"]
            print(asset_id, column_name, new_value)

            message = "Asset {} - {} has a new value: {}.".format(asset_id, column_name, new_value)

            # 게이트웨이 스코프에선 아래 메시지 박스가 뜨지 않음 (Vision 전용)
            # system.gui.messageBox(message, "Alarm Notification")
            # → 대안: 태그 알람, 파이프라인, Perspective 메시지 등 사용
