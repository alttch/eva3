#include <SPI.h>
#include <Ethernet.h>
#include <EthernetUdp.h>

// motion sensors pins
int mPin1 = 2;
int mPin2 = 3;

// motion sensor states
int mNow1 = 1;
int mNow2 = 1;

// previous motion sensor states
int mOld1 = 0;
int mOld2 = 0;

// signal LED pin
int lPin = 7;

int toLedSeconds = 0;

// EVA ICS UC IP
IPAddress aSrvIP(192, 168, 1, 11);
int aSrvPort = 8881;

byte mac[] = {  
  0x00, 0xAA, 0xBB, 0xCC, 0xDE, 0x01 };

EthernetUDP Udp;

void(* resetFunc) (void) = 0;

void setup() {
  pinMode (mPin1,INPUT);
  pinMode (mPin2, INPUT);
  pinMode (lPin, OUTPUT);
  Serial.begin(9600);
  Serial.print("Waiting for sensor calibration...");
  for (int i=10;i>0;i--) {
    Serial.print(i,DEC);
    Serial.print(" ");
    digitalWrite(lPin,HIGH);
    delay(500);
    digitalWrite(lPin,LOW);
    delay(500);
  }
  Serial.println();
  Serial.println("Motion sensor calibration check...");
  while ((mNow1+mNow2)!=0) {
    updateSensors();
    delay(10);
  }
  Serial.print("Configuring ethernet...");
  if (Ethernet.begin(mac) == 0) {
    Serial.println("Failed, restarting in 5 seconds");
    for (int i=0;i<2;i++) {
     digitalWrite(lPin,HIGH);
     delay(500);
     digitalWrite(lPin,LOW);
     delay(500);
    }
    delay(3000);
    resetFunc();
    return;
    }
  for (byte thisByte = 0; thisByte < 4; thisByte++) {
    // print the value of each byte of the IP address:
    Serial.print(Ethernet.localIP()[thisByte], DEC);
    Serial.print(".");
  }
  Serial.println();
  Serial.println("Started");
  // blink signal LED 3 times
  Udp.begin(aSrvPort);
  for (int i=0;i<3;i++) {
    digitalWrite(lPin,HIGH);
    delay(200);
    digitalWrite(lPin,LOW);
    delay(200);
  }
}

void updateSensors() {
  mNow1 = digitalRead(mPin1);
  mNow2 = digitalRead(mPin2);
}

void sendNotify(char* sensor,int value) {
  char p[100];
  char v[10];
  strcpy(p,sensor);
  strcat(p," u None ");
  itoa(value,v,10);
  strcat(p,v);
  strcat(p,0);
  Udp.beginPacket(aSrvIP,aSrvPort);
  Udp.write(p);
  Udp.endPacket();
}

void loop() {
  updateSensors();
  if (mNow1!=mOld1) {
    mOld1=mNow1;
    Serial.print("Motion sensor 1 value change: ");
    Serial.println(mNow1,DEC);
    if (mNow1>0) toLedSeconds=3000;
    sendNotify("sensor:security/motion1",mNow1);
  }
  if (mNow2!=mOld2) {
    mOld2=mNow2;
    Serial.print("Motion sensor 2 value change: ");
    Serial.println(mNow2,DEC);
    if (mNow2>0) toLedSeconds=3000;
    sendNotify("sensor:security/motion2",mNow2);
  }
  if (toLedSeconds--==3000) digitalWrite(lPin,HIGH);
  if (toLedSeconds==0) digitalWrite(lPin,LOW);
  delay(1);
}
