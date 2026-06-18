flowchart TB

  subgraph Client["Cliente"]

    Mobile["App móvil / cliente"]

  end

  Mobile -->|HTTP REST| SecurityController

  subgraph Backend["Atom Backend (Spring Boot, Java 21)"]

    direction TB

    subgraph Inbound["Adaptadores de entrada"]

      SecurityController["SecurityController<br/>/api/v1/security"]

      UserIn["UserInAdapter<br/>(pendiente)"]

    end

    subgraph App["Aplicación (Hexagonal)"]

      direction LR

      InPorts["Puertos IN<br/>InputValidationPort<br/>DeviceSecurityPort<br/>ExecuteCommandPortIn<br/>StreamChatPortIn<br/>UserPortIn<br/>ChatPortIn"]

      UseCases["Casos de uso<br/>InputValidationUsecase<br/>DeviceSecurityUseCase<br/>ExternalCommandUseCase<br/>ExternalMessageUseCase<br/>UserUseCase"]

      OutPorts["Puertos OUT<br/>ExternalInteractionPortOut<br/>DeviceInspectorPort<br/>PasswordEncoderPortOut<br/>UserPortOut<br/>ChatPortOut"]

      InPorts --> UseCases --> OutPorts

    end

    subgraph Domain["Dominio"]

      Models["Modelos<br/>User, Chat, Message<br/>DeviceSecurityStatus<br/>ValidationResult, RiskLevel"]

      DomainEx["Excepciones de negocio<br/>InputValidationException<br/>DeviceSecurityException"]

    end

    subgraph Infra["Infraestructura"]

      direction LR

      Grpc["InteractionGrpcAdapter (gRPC)"]

      Device["DeviceInspectorAdapter"]

      Encoder["Argon2PasswordEncoderAdapter"]

      UserOut["UserOutAdapter (pendiente)"]

      Mapper["UserMapper (pendiente)"]

      Entities["Entidades Mongo<br/>UserEntity, ChatEntity, MessageEntity"]

      Aspect["DeviceSecurityAspect<br/>@SecureOperation"]

      Handler["Securityexceptionhandler"]

    end

    SecurityController --> InPorts

    UseCases --> Models

    UseCases --> DomainEx

    OutPorts --> Grpc

    OutPorts --> Device

    OutPorts --> Encoder

    OutPorts --> UserOut

    UserOut --> Mapper --> Entities

    SecurityController --> Handler

    Aspect -. valida integridad .-> UseCases

  end

  Grpc -->|ai.proto / AtomAgentService| Python["Servicio Python AI (externo)"]

  Device --> Runtime["Entorno de dispositivo / SO"]

  Entities --> Mongo["MongoDB Atlas"]

  classDef pending stroke-dasharray: 5 5;

  class UserIn,UserOut,Mapper pending;