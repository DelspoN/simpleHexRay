# -*- encoding: utf-8 -*-

def sizeOfOpnd(disasm):
	disasmSplitted = disasm.split()
	if len(disasmSplitted) == 1:
		return 0
	else:
		if "," in disasmSplitted[1]:
			return 2
		else:
			return 1

def skipProEpilogue(fullDisasm):
	patchedDisasm = fullDisasm
	patchedDisasm = patchedDisasm.replace("push rbp\n", "")
	patchedDisasm = patchedDisasm.replace("mov rbp,rsp\n", "")
	patchedDisasm = patchedDisasm.replace("pop rbp\n", "")
	patchedDisasm = patchedDisasm.replace("leave\n", "")
	patchedDisasm = patchedDisasm.replace("retn\n", "")
	patchedDisasm = patchedDisasm.replace("ret\n", "")

	if "sub rsp," in patchedDisasm:
		stackSize = patchedDisasm.split("sub rsp,")[1].split("\n")[0]
		patchedDisasm = patchedDisasm.replace("sub rsp,"+stackSize+"\n", "")
	return patchedDisasm

def getFullDisasm():
	startPoint, endPoint = Chunks(here()).next()
	nowPoint = startPoint

	fullDisasm = ''

	while(nowPoint < endPoint):
		fullDisasm += GetDisasm(nowPoint) + "\n"
		nowPoint = NextHead(nowPoint)

	# For parsing
	while("  " in fullDisasm):
		fullDisasm = fullDisasm.replace("  ", " ")
	fullDisasm = fullDisasm.replace(", ", ",")
	return fullDisasm

def processIns(disasm):
	disasm = disasm.replace("offset format; ","")

	tmp = disasm.split("mov ")

	for i in range(len(tmp)-1):
		target = tmp[i+1].split(",")[0]
		value = tmp[i+1].split(",")[1].split()[0]
		disasm = disasm.replace("mov "+target+","+value, target+"="+value)

	tmp = disasm.split("imul ")

	for i in range(len(tmp)-1):
		target = tmp[i+1].split(",")[0]
		value = tmp[i+1].split(",")[1].split()[0]
		disasm = disasm.replace("imul "+target+","+value, target+"="+target+"*"+value)

	tmp = disasm.split("add ")

	for i in range(len(tmp)-1):
		target = tmp[i+1].split(",")[0]
		value = tmp[i+1].split(",")[1].split()[0]
		disasm = disasm.replace("add "+target+","+value, target+"="+target+"+"+value)
	return disasm

def simplifyEx(disasm):
	# Processing local variables
	disasm = disasm.replace("[rbp+", "")
	disasm = disasm.replace("]", "")

	# Processing eax after call
	tmp = disasm.split("\n")
	for i in range(len(tmp)-1):
		if "call" not in tmp[i]:
			continue

		if "=" not in tmp[i+1]:
			continue

		target, value = tmp[i+1].split("=")
		if "eax" in target:
			continue
		if "eax" in value:
			newValue = value.replace("eax", tmp[i])
			disasm = disasm.replace(tmp[i]+"\n", "")
			disasm = disasm.replace(tmp[i+1], target+"="+newValue)

	# Simplifying the expression
	prevDisasm = ""
	k=0
	tmp = disasm.split("\n")
	while (k < len(tmp)):
		tmp = disasm.split("\n")
		if "=" not in tmp[k]:
			k += 1
			continue
		aFlag=0
		target, value = tmp[k].split("=")
		for i in range(k+1, len(tmp)):
			if "=" not in tmp[i]:
				continue
			tmp2=tmp[i].split("=")
			if target in tmp2[1]:
				prevDisasm = disasm
				newValue = tmp2[1].replace(target, value)
				if ("var" in target)&("edi" not in value)&("esi" not in value)&("edx" not in value):
					continue
				disasm = disasm.replace(target + "=" + value + "\n", "")
				disasm = disasm.replace(tmp[i], tmp2[0]+"="+newValue)
				aFlag += 1
			if target in tmp2[0]:
				break
		if aFlag == 0:
			k += 1
	return disasm

def processCall(disasm):
	tmp = disasm.split("call ")
	for i in range(len(tmp)-1):
		tmp2 = tmp[i].split("\n")
		arg = []
		for j in range(len(tmp2)-2, -1, -1):
		# Checking arguments by parsing target and value
			if "=" in tmp2[j]:
				target, value = tmp2[j].split("=")
				if target in ['edi', 'esi', 'edx']:
					arg.append(value)
					disasm = disasm.replace(target+"="+value+"\n", "")
			else:
				break

		param = ""
		for j in range(len(arg)):
			param += arg[j]+","
		param = param[:-1]		# To delete comma at last of string

		funcName = tmp[i+1].split()[0]
		disasm = disasm.replace("call " + funcName, funcName+"("+param+")")
	disasm = disasm.replace("eax=0\n_printf", "_printf")
	return disasm

def processRet(disasm):
	tmp = disasm.split("\n")
	for i in range(len(tmp)-1,-1, -1):
		if "(" in tmp[i]:
			disasm = disasm.replace(tmp[i], "return "+tmp[i])
			break
		if "eax=" in tmp[i]:
			newValue = tmp[i].replace("eax=", "return ")
			disasm = disasm.replace(tmp[i], newValue)
			break
	return disasm

def processArg(disasm):
	# Simplify arguments
	disasm = disasm.replace("edi", "arg_1")
	disasm = disasm.replace("esi", "arg_2")
	disasm = disasm.replace("edx", "arg_3")
	return disasm

def processType(funcName, disasm):
	argument=""
	chFlag=0

	# For ass01, only 4byte type used. So I set type always integer.
	# If another type is used, you have to check the type by checking value of variables.
	for i in range(1,9):
		if "arg_"+str(i) in disasm:
			chFlag=1
			argument += "int arg_"+str(i)+","
	if chFlag:
		argument = argument[:-1]
	code = "int " + funcName + "("+argument+")\n"
	code += "{\n"

	tmp = disasm.split("\n")
	target=[]
	for i in range(len(tmp)):
		if "=" not in tmp[i]:
			code += tmp[i] + "\n"
			continue
		trgt = tmp[i].split("=")[0]
		if trgt not in target:
			code += "int "+tmp[i]+"\n"
			target.append(trgt)
			continue
		code += tmp[i]+"\n"
	code += "}\n"
	return code

def simpleHexRay():
	funcName = GetFunctionName(here())
	fullDisasm = getFullDisasm()
	fullDisasm = skipProEpilogue(fullDisasm)
	fullDisasm = processIns(fullDisasm)
	fullDisasm = simplifyEx(fullDisasm)
	fullDisasm = processCall(fullDisasm)
	fullDisasm = processRet(fullDisasm)
	fullDisasm = processArg(fullDisasm)
	code = processType(funcName, fullDisasm)
	print code

"""
1. 프롤로그 / 에필로그 : 컴파일러에 의해 자동적으로 작성되는 부분
	1.1 PROLOGUE
		push rbp
		mov rbp, rsp
	1.2 EPILOGUE
		leave
		ret

2. 변수
	2.1 [rbp-?]	: 지역 변수
	2.2 [edi]	: 1번째 인자
	2.3 [esi]	: 2번째 인자
	2.4 [edx]	: 3번째 인자

3. 기타
	3.1 함수가 끝날 때 즈음 rax에 값이 담기는데 그 값은 함수의 return 값이다.
	3.2 함수의 시작부에 sub rsp,0x10을 하는데 이는 지역변수를 사용할 공간을 스택에서 확보하기 위함이다.
	3.3 edi가 사용되면 반드시 뒤에서 함수를 호출한다.
	3.4 call 뒤에서 eax가 쓰이는데 이는 함수의 반환 값이다.
	3.5 printf 앞에서 eax를 0으로 초기화한다.
"""