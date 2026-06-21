---
id: desenvolvimento-software/boas-praticas-de-desenvolvimento-de-software
titulo: Boas Práticas de Desenvolvimento de Software
assunto: desenvolvimento-software
nivel: intermediario
resumo: Boas práticas focam em encapsulamento, nomenclatura clara e arquiteturas como
  Onion para desenvolver software legível, seguro e fácil de manter.
status: publicado
referencias: []
atualizado_em: '2026-06-20'
---

# Boas Práticas de Desenvolvimento de Software

Este guia apresenta algumas boas práticas fundamentais para desenvolvedores, focando em como escrever código mais legível, seguro e fácil de manter.

## 1. Encapsulamento e Testabilidade

O princípio do encapsulamento ajuda a proteger o estado interno do seu código e facilita a manutenção e os testes.

*   **Funções Públicas vs. Privadas:** É mais interessante trabalhar com funções públicas, pois elas são mais fáceis de testar e entender o fluxo de execução. Evite o uso excessivo de funções privadas, a menos que seja estritamente necessário para a arquitetura do sistema.

## 2. Controle de Acesso a Dados

Para evitar a exposição de dados que não devem ser acessíveis a outros módulos, utilize mecanismos de controle de acesso.

*   **Separação de Módulos:** Em vez de expor variáveis diretamente, utilize a passagem de dados entre módulos. Isso garante que o fluxo de informação seja controlado e que o estado interno do seu código seja protegido.

## 3. Nomenclatura Clara

A forma como nomeamos variáveis e funções impacta diretamente a legibilidade do código.

*   **Nomes Significativos:** Os nomes das variáveis devem ser significativos e relacionados ao domínio do problema que estão representando.
    *   **Ruim:** `a > b`
    *   **Bom:** `userAge` (em vez de apenas `a`)

## 4. Arquitetura de Aplicações Backend

Para aplicações backend, é fundamental utilizar um padrão de arquitetura para organizar os arquivos e garantir a escalabilidade e a manutenibilidade do código. Sugerimos as seguintes abordagens:

*   **Clean Architecture**
*   **Onion Architecture**
*   **Hexagonal Architecture**

Recomendamos a **Onion Architecture** para iniciantes, pois ela foca na separação de preocupações, facilitando a compreensão do fluxo de dados.

### Estruturas de Diretórios (Exemplo: Cadastro de Usuário)

Abaixo estão exemplos conceituais de como as estruturas de diretórios podem ser organizadas para cada padrão, focando na separação de responsabilidades.

#### Clean Architecture

Esta arquitetura foca na separação estrita das regras de negócio (o domínio) das preocupações de infraestrutura (banco de dados, frameworks).

```
/projeto
├── domain/          # Regras de negócio puras (Entidades, Casos de Uso)
│   └── user.entity.ts
├── application/     # Casos de Uso (Orquestração das regras)
│   └── user.service.ts
├── infrastructure/  # Implementação de detalhes (BD, APIs)
│   ├── persistence/ # Repositórios e acesso ao banco de dados
│   │   └── user.repository.ts
│   └── api/         # Controllers e endpoints
│       └── user.controller.ts
└── index.ts         # Ponto de entrada da aplicação
```

#### Onion Architecture

Esta arquitetura enfatiza a dependência reversa, onde as camadas internas dependem apenas das regras de negócio centrais.

```
/projeto
├── domain/          # Regras de negócio centrais (o núcleo)
│   └── user.entity.ts
├── application/     # Casos de Uso (Lógica de aplicação)
│   └── user.service.ts
├── infrastructure/  # Detalhes externos (BD, Web, etc.)
│   ├── persistence/ # Implementação do banco de dados
│   │   └── user.repository.ts
│   └── presentation/ # Controllers e interfaces de entrada/saída
│       └── user.controller.ts
└── index.ts         # Ponto de entrada da aplicação
```

#### Hexagonal Architecture

Esta arquitetura isola o domínio (o "hexágono") das tecnologias externas, focando na portabilidade e na facilidade de troca de infraestrutura.

```
/projeto
├── domain/          # O núcleo do negócio (Regras de negócio)
│   └── user.entity.ts
├── ports/           # Interfaces (Portas de entrada e saída)
│   ├── in/           # Portas de entrada (o que o sistema pode fazer)
│   │   └── user.service.interface.ts
│   └── out/          # Portas de saída (como o sistema interage com o mundo)
│       └── user.repository.interface.ts
├── adapters/        # Implementações concretas (Infraestrutura)
│   ├── persistence/ # Implementação do banco de dados
│   │   └── postgres.repository.ts
│   └── web/         # Implementação da API
│       └── express.controller.ts
└── main.ts          # Ponto de inicialização
```

Posso gerar o documento?
