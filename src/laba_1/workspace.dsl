workspace {
    name "Ride Booking System"
    description "Сервис заказа поездок (C4 модель)"

    # включаем режим с иерархической системой идентификаторов
    !identifiers hierarchical

    model {

        // Люди (actors)
        passenger = person "Пассажир"
        driver = person "Водитель"
        admin = person "Администратор"

        // Внешние системы
        paymentSystem = softwareSystem "Платежная система"
        smsService = softwareSystem "SMS сервис"
        emailService = softwareSystem "Email сервис"

        // Наша система
        rideSystem = softwareSystem "Сервис заказа поездок" {

            // Containers внутри rideSystem
            userMobile = container "User Mobile App" {
                technology "iOS/Android, Kotlin/Swift, HTTP"
            }

            driverMobile = container "Driver Mobile App" {
                technology "iOS/Android, Kotlin/Swift, HTTP"
            }

            adminWeb = container "Admin Web App" {
                technology "React SPA, TypeScript, HTML/CSS"
            }

            database = container "Relational Database" {
                technology "PostgreSQL, JDBC"
            }

            paymentService = container "Payment Service" {
                technology "Java, Spring Boot"
                -> paymentSystem "Вызывает API платежной системы" "HTTPS/REST"
                -> database "Читает и пишет данные о платежах" "JDBC"
            }

            notificationService = container "Notification Service" {
                technology "Java, Spring Boot"
                -> smsService "Отправляет SMS" "HTTPS/REST"
                -> emailService "Отправляет email" "SMTP"
            }

            userService = container "User Service" {
                technology "Java, Spring Boot"
                -> database "Читает и пишет данные пользователей" "JDBC"
                -> notificationService "Запрашивает отправку уведомлений при регистрации" "HTTP/REST"
            }

            driverService = container "Driver Service" {
                technology "Java, Spring Boot"
                -> database "Читает и пишет данные водителей" "JDBC"
            }

            tripService = container "Trip Service" {
                technology "Java, Spring Boot"
                -> database "Читает и пишет данные поездок" "JDBC"
                -> paymentService "Запрашивает создание/подтверждение платежа за поездку" "HTTP/REST"
                -> notificationService "Запрашивает отправку уведомлений о статусе поездки" "HTTP/REST"
                -> userService "Запрашивает данные пользователя при создании поездки" "HTTP/REST"
            }

            apiGateway = container "API Gateway" {
                technology "Java, Spring Boot, REST API"
                -> userService "Маршрутизирует запросы пользователей (регистрация, поиск)" "HTTP/REST"
                -> driverService "Маршрутизирует запросы водителей (регистрация)" "HTTP/REST"
                -> tripService "Маршрутизирует запросы, связанные с поездками" "HTTP/REST"
            }
        }

        // Связи system context
        passenger -> rideSystem "Вызывает API для управления поездками" "HTTPS/REST"
        driver -> rideSystem "Вызывает API для управления заказами" "HTTPS/REST"
        admin -> rideSystem "Использует интерфейс администратора" "HTTPS/REST"

        rideSystem -> paymentSystem "Создаёт и подтверждает платежи за поездки" "HTTPS/REST"
        rideSystem -> smsService "Отправляет SMS-уведомления" "HTTPS/REST"
        rideSystem -> emailService "Отправляет email-уведомления" "SMTP"

        // Связи контейнеров (клиентские приложения -> API)
        passenger -> rideSystem.userMobile "Использует мобильное приложение пассажира" "HTTP/HTTPS"
        driver -> rideSystem.driverMobile "Использует мобильное приложение водителя" "HTTP/HTTPS"
        admin -> rideSystem.adminWeb "Использует веб-интерфейс администратора" "HTTPS"

        rideSystem.userMobile -> rideSystem.apiGateway "Вызывает REST API" "HTTPS/REST"
        rideSystem.driverMobile -> rideSystem.apiGateway "Вызывает REST API" "HTTPS/REST"
        rideSystem.adminWeb -> rideSystem.apiGateway "Вызывает REST API" "HTTPS/REST"
    }

    views {

        themes default

        // Dynamic view: сценарий 'Создание заказа поездки'
        dynamic rideSystem "uc-create-trip" "Создание заказа поездки пассажиром" {
            autoLayout lr

            passenger -> rideSystem.userMobile "Открывает экран создания поездки"
            rideSystem.userMobile -> rideSystem.apiGateway "POST /trips"
            rideSystem.apiGateway -> rideSystem.tripService "Создать поездку"
            rideSystem.tripService -> rideSystem.userService "Проверить, что пользователь существует и активен"
            rideSystem.tripService -> rideSystem.paymentService "Запросить предварительную авторизацию платежа"
            rideSystem.paymentService -> paymentSystem "Вызов API платежной системы"
            paymentSystem -> rideSystem.paymentService "Результат авторизации"
            rideSystem.paymentService -> rideSystem.tripService "Подтверждение статуса оплаты"
            rideSystem.tripService -> rideSystem.database "Сохранить новую поездку со статусом 'Создана'"
            rideSystem.tripService -> rideSystem.notificationService "Отправить уведомление водителям об активном заказе"
            rideSystem.notificationService -> smsService "SMS/Push водителям (опционально)"
            rideSystem.tripService -> rideSystem.apiGateway "Вернуть данные созданной поездки"
            rideSystem.apiGateway -> rideSystem.userMobile "HTTP 201 с деталями поездки"
        }

        // C1: System Context
        systemContext rideSystem {
            include *
            autoLayout
        }

        // C2: Container View (vertical)
        container rideSystem "vertical" {
            include *
            autoLayout
        }

        // C2: Container View (horizontal)
        container rideSystem "horizontal" {
            include *
            autoLayout lr
        }
    }
}
