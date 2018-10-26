all:
	gcc -fPIC -shared -I/usr/include/python3.6 -o evacpp.so evacpp.cpp `pkg-config --cflags --libs python3` -lstdc++ -lboost_python3-py36
	#python3 test.py
	echo "import evacpp"|python3
