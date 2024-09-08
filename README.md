# Integrated Smart Home Monitoring and Security System

## CITS5506 Group11 members

| UWA ID  | Name | Github Username |
|---------|------|-----------------|
|10994619 |Jay Lee|10994619|
|23884492 |Zihan Wu|Zihan22|
|23824629 |Gawen Hei|CallMeHeiSir|
|22496593 |Jordan Rigden|jordanrigden|
|24090236 |Konstantin Tagintsev|ktagintsev|

## Project Overview

The system aims to enhance home security and environmental monitoring by integrating a variety of sensors and communication modules. The system is controlled via a Telegram bot, offering real-time updates and remote management. The system continuously monitors environmental factors like temperature, humidity, and carbon dioxide levels while also ensuring security through real-time surveillance.

## Functional Requirements

1. The system should allow users to remotely control smart home devices via a Telegram bot.
2. The system should provide the ability to activate/deactivate the security mode through the Telegram bot.
3. The system should provide real-time video streaming from the indoor camera through the Telegram bot.
4. The system should continuously monitor indoor and outdoor humidity, temperature, and CO2 levels.
5. The system should log all indoor and outdoor environmental data for real-time and historical analysis.
6. The system should detect an abnormal CO2 level indicative of fire or smoke and immediately send an alert to the user via the Telegram bot.
7. The system should detect indoor movement when security mode is active and send a notification to the user through the Telegram bot, including an image of the detected movement.
8. The system should provide the ability for users to request real-time/historical humidity, temperature, and CO2 data for both indoor and outdoor environments.
9. The system should compare indoor and outdoor humidity, temperature, and CO2 readings against user-defined thresholds and send notifications to the user when the readings exceed or fall below these thresholds.
10. The system should automatically remove historical data that is older than 1 year.

## Non-Functional Requirements

1. The system should automatically resume operation after the device reboots.
2. The system should be able to handle errors gracefully and continue operation without interruption.
3. The system should process and respond to user commands through the Telegram bot within 5 seconds.
4. All data communication between the devices and the Telegram bot should be encrypted.
