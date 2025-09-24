import csv
import datetime
import StringIO

def importDevicesFromCSV():
    # 파일 선택 창을 띄워 사용자에게 CSV 파일을 선택하게 함
    filePath = system.file.openFile("csv", "CSV Files")
    
    if filePath is None:
        return
    
    # CSV 파일을 읽고 장치 추가 함수 호출
    with open(filePath, 'r') as csvFile:
        reader = csv.DictReader(csvFile)
        
        for row in reader:
            # 각 장치의 속성 설정
            deviceType = row.get('DeviceType', '')
            deviceName = row.get('DeviceName', '')
            hostName = row.get('Address', '')
            port = int(row.get('Port', 102))  # 기본 포트는 102로 설정
            requestTimeout = row.get('RequestTimeout', '')
            
            # 장치 속성 딕셔너리 생성
            deviceProps = {
                "HostName": hostName,
                "Port": port,
                "RequestTimeout": requestTimeout
            }
            
            # 장치를 Ignition에 추가
            try:
                system.device.addDevice(deviceType=deviceType,
                                        deviceName=deviceName,
                                        deviceProps=deviceProps)
                print("Device added:", deviceName)
            except Exception as e:
                print("Failed to add device:", deviceName, "-", str(e))
                
def exportDevicesToCSV():
    # 모든 장치 목록 가져오기
    devices = system.device.listDevices()        
   
    # CSV 데이터를 메모리에 저장하기 위한 StringIO 객체 생성
    output = StringIO.StringIO()
    
    # CSV 열 순서 지정
    fieldnames = [
        'DeviceName',
        'DeviceType',
        'Address',
        'Port',
        'Enabled',
        'State',
        'RequestTimeout'
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)    
    
    # CSV 파일에 헤더 작성
    writer.writeheader()
    
    # 각 장치의 정보를 CSV에 기록
    # labworksim, InternalOpc 제외
    
    for i in range(2,devices.getRowCount()):
		name = devices.getValueAt(i, 0)
		enable = devices.getValueAt(i, 1)
		state = devices.getValueAt(i, 2)
		driver = devices.getValueAt(i, 3)
#		hostName = system.device.getDeviceHostname(name)
#		print(hostName)
#        port = devices.getValueAt(i,5)

		try:
			address = system.device.getDeviceHostname(name)
		except:
			address = ''
			
		drv = driver.lower()
		
		if 'modbus'in drv:
			port = 502
		else:
			port = 102
        
        # CSV에 기록할 데이터 형식
		row = {
		    'DeviceName':  name,
		    'DeviceType':  driver,
		    'Address':  address ,
		    'Port': port ,
		    'Enabled':  enable,
		    'State': state,
		    'RequestTimeout':  ''
		}
        
        # CSV 파일에 한 행 기록
		writer.writerow(row)
        
    # CSV 데이터 가져오기
    csvData = output.getvalue()
    
    # 사용자에게 파일을 저장 위치 선택
    now = datetime.datetime.now().strftime('%Y%m%d')
    filePath = system.file.saveFile("Devices-" + now + ".csv")
    
    if filePath is not None:
        # 파일에 데이터를 씀
        system.file.writeFile(filePath, csvData)
    	print('Tags exported to:', filePath)
    	
def exportDevicesToCSV1():
    # 모든 장치 목록 가져오기
    devices = system.device.listDevices()
    
    # CSV 데이터를 메모리에 저장하기 위한 StringIO 객체 생성
    output = StringIO.StringIO()
    
    # CSV 열 순서 지정
    fieldnames = [
        'DeviceName',
        'DeviceType',
        'Address',
        'Port',
        'Enabled',
        'State',
        'RequestTimeout'
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    
    # CSV 파일에 헤더 작성
    writer.writeheader()
    
    # 각 장치의 정보를 CSV에 기록
    # labworksim, InternalOpc 제외
    pydataset = system.dataset.toPyDataSet(devices)
    
    for i in pydataset:
    	if i['Enabled']:
    		name = i['Name']
    		enable = i['Enabled']
    		state = i['State']
    		driver = i['Driver']
    		hostname = system.device.getDeviceHostname(name)
    		if driver == 'com.inductiveautomation.Iec61850DeviceType':
    			port = '102'
    		elif driver == 'ModbusTcp':
    			port = '502'
    		else:
    			port = 0
    		
    		row = {
            'DeviceName':  name,
            'DeviceType':  driver,
            'Address':  hostname,
            'Port':  port,
            'Enabled':  enable,
            'State': state,
            'RequestTimeout':  ''
        	}
            
	        # CSV 파일에 한 행 기록
	        writer.writerow(row)
        
    # CSV 데이터 가져오기
    csvData = output.getvalue()
    
    # 사용자에게 파일을 저장 위치 선택
    now = datetime.datetime.now().strftime('%Y%m%d')
    filePath = system.file.saveFile("Devices-" + now + ".csv")
    
    if filePath is not None:
        # 파일에 데이터를 씀
        system.file.writeFile(filePath, csvData)
    	print('Tags exported to:', filePath)
    
def removeDevices(filter=None):
	# 현재 모든 장치 목록 가져오기
	devices = system.device.listDevices()
	
	# 삭제할 장치 목록 설정
	devicesToRemove = []

    # labworksim, InternalOpc 제외
	for i in range(2,devices.getRowCount()):
		if filter:
			name = devices.getValueAt(i, 'name')
			if filter in name:
				devicesToRemove.append(name)
		else:
			name = devices.getValueAt(i, 'name')
			devicesToRemove.append(name)
			
	for deviceName in devicesToRemove:
	    try:
	        system.device.removeDevice(deviceName)
	        print("Device '{}' has been removed.".format(deviceName))
	    except Exception as e:
	        print("Error removing device '{}': {}".format(deviceName,e))
	     
		   
def restart_devices(device):
	try:
		system.device.restart(device)
#		system.util.getLogger('DeviceRestart').info("Restart device : {}".format(device))
	except Exception as e:
		system.util.getLogger('DeviceRestart').error("Error Restart device {} : {}".format(device, e))
		
def restart(tags):
	import system

	badCode = [512]  # 512: Bad / 522: Bad_NotConnected / 527: Bad_Failure
	restart = []
	
	for i, tag in enumerate(system.tag.readBlocking(tags)):
		cnt = 0
		for k in tag.value.keys(): # udt 태그 중에 Fq를 제외한 태그만 검사
			if 'Fq' not in k:
				path = tags[i] + '/' + k
				try:
					code = system.tag.readBlocking(path)[0].quality.getCode() & 0xFFFF # 태그 코드
					opcPath = system.tag.readBlocking(path + '.OpcItemPath')[0].value # 태그 경로
					if opcPath and code in badCode:
						devices = system.device.listDevices()
						devices = system.dataset.toPyDataSet(devices)
						device = opcPath.split('[')[1].split(']')[0] # 디바이스 이름 추출
						for d in devices:
							if device == d[0] and d[2] == 'Connected':  # d[0]: 디바이스 이름 / d[1]: Enable / d[2]: 연결 상태
								cnt += 1
								break
						if cnt >= 5:
							restart.append(device)								# 계전기 태그 중에 bad 5개 이상이면 restart
							break
				except Exception as e:
					system.util.getLogger('DeviceRestart').warn("Error reading {} : {}".format(path, e))

	for device in restart:
		if device:
			system.util.getLogger('DeviceRestart').info("Restart device : {}".format(device))
			system.util.invokeAsynchronous(lambda d=device: restart_devices(d))  # 디바이스 재시작이 오래 걸려서 비동기로 실행
