int relayPin = 7;  // Pin connected to relay
int ledPin = 8;    // Pin connected to LED

void setup() {
  pinMode(relayPin, OUTPUT);  // Set relay pin as output
  pinMode(ledPin, OUTPUT);    // Set LED pin as output

  // Start motor immediately when Arduino boots
  digitalWrite(relayPin, HIGH);  // Relay ON, Motor starts
  digitalWrite(ledPin, LOW);     // LED OFF initially
  Serial.begin(9600);            // Begin Serial communication
}

void loop() {
  if (Serial.available()) {
    char command = Serial.read();  // Read incoming command from Python

    // Check for drowsiness alert from Python
    if (command == '1') {
      digitalWrite(relayPin, HIGH);   // Stop the motor
      digitalWrite(ledPin, HIGH);    // Start blinking LED (drowsiness alert)
      delay(500);
      digitalWrite(ledPin, LOW);     // Turn off LED
      delay(500);
    } 
    // If no drowsiness, continue motor operation
    else if (command == '0') {
      digitalWrite(relayPin, LOW);  // Start motor again
      digitalWrite(ledPin, LOW);     // Turn off LED
    }
  }
}
