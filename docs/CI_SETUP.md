# GitHub Actions와 외부 tenant Foundry 설정

일반 CI는 credential 없이 자동 실행됩니다. Microsoft Foundry 실환경 검증은 `foundry-external` GitHub Environment와 OIDC federation을 구성한 뒤 수동으로 실행합니다. API key, client secret, OpenAI token은 저장하지 않습니다.

## 1. GitHub Environment

저장소의 **Settings → Environments**에서 `foundry-external`을 만듭니다. **Deployment branches and tags**는 `main` branch만 허용하도록 제한합니다. 외부 tenant 권한이 중요한 환경이면 required reviewer도 지정합니다. workflow 자체도 `main`이 아닌 ref에서는 job을 실행하지 않지만, Environment branch 정책이 수정된 branch의 workflow까지 차단하는 최종 경계입니다.

Environment secret:

| 이름 | 값 |
| --- | --- |
| `AZURE_CLIENT_ID` | 외부 tenant에 있는 Entra application/service principal의 client ID |
| `AZURE_TENANT_ID` | Foundry resource가 속한 외부 tenant ID |
| `AZURE_SUBSCRIPTION_ID` | Foundry resource가 속한 subscription ID |

Environment variable:

| 이름 | 필수 | 값 |
| --- | --- | --- |
| `FOUNDRY_PROJECT_ENDPOINT` | 예 | `https://<account>.services.ai.azure.com/api/projects/<project>` |
| `FOUNDRY_MODEL` | 예 | catalog model ID가 아닌 실제 deployment 이름 |
| `FOUNDRY_RESOURCE_GROUP` | 임시 배포 삭제 시 | Foundry account의 resource group |
| `FOUNDRY_ACCOUNT_NAME` | 임시 배포 삭제 시 | project 이름이 아닌 Foundry/Cognitive Services account 이름 |

세 ID는 암호 자체는 아니지만 OIDC trust 구성을 한 Environment 안에 모으기 위해 secret으로 관리합니다. endpoint와 deployment는 GitHub variable로 관리하므로 workflow 파일에 tenant별 값을 넣지 않습니다.

## 2. 외부 tenant OIDC federation

외부 tenant의 Entra application에 federated identity credential을 추가합니다.

| claim | 값 |
| --- | --- |
| issuer | `https://token.actions.githubusercontent.com` |
| subject | `repo:hyeonsangjeon/pronunciation-mapper:environment:foundry-external` |
| audience | `api://AzureADTokenExchange` |

이 저장소는 2025년에 생성되었고 현재 기본 subject 형식과 non-immutable subject 설정을 사용합니다. 저장소 이전, 이름 변경 또는 GitHub의 immutable subject opt-in 뒤에는 [OIDC subject 설정](https://docs.github.com/en/actions/reference/security/oidc)을 다시 확인하고 Entra credential을 갱신해야 합니다.

OIDC client secret은 만들 필요가 없습니다. workflow의 `id-token: write` 권한과 [`Azure/login`](https://github.com/Azure/login)이 짧은 수명의 GitHub OIDC token을 외부 tenant의 Azure access token으로 교환합니다.

## 3. 최소 Azure RBAC

실환경 추론에는 service principal에 현재 이름 `Foundry User`(이전 이름 `Azure AI User`, role ID `53ca6127-db72-4b80-b1b0-d745d6d5456d`) 역할을 Foundry resource/account scope로 부여하는 구성이 가장 단순합니다. project 단위 격리가 필요하면 Foundry resource의 `Reader`와 project scope의 `Foundry User` 조합을 사용합니다. `Owner`나 `Contributor`만으로는 Foundry data-plane 추론 권한이 생기지 않습니다.

임시 deployment 삭제는 별도의 control-plane 권한입니다. 삭제 기능을 사용해야 할 때만 해당 identity에 deployment delete 권한이 포함된 custom role, `Foundry Account Owner`, `Foundry Owner` 또는 `Contributor`를 Foundry account의 최소 scope로 추가합니다. 자세한 역할 차이는 [Microsoft Foundry RBAC](https://learn.microsoft.com/azure/foundry/concepts/rbac-foundry)을 참고하세요.

## 4. 실환경 테스트 실행

GitHub의 **Actions → Foundry live integration → Run workflow**에서 실행합니다.

- `deployment`을 비우면 Environment variable `FOUNDRY_MODEL`을 사용합니다.
- 기존 배포를 검사할 때 `cleanup_temporary_deployment`는 반드시 꺼둡니다.
- 미리 만든 임시 배포를 검사하려면 이름을 `ci-`로 시작하고 `deployment`에 그 이름을 입력합니다. 테스트 후 삭제하려는 경우에만 cleanup을 켭니다.

workflow는 다음을 모두 만족해야 성공합니다.

1. `fallback_strategy="raise"`인 집중 테스트가 실제 Foundry 응답으로 `트랜잭숑 → transaction`을 선택합니다.
2. golden set exact accuracy가 1.0입니다.
3. fallback rate가 0이고 실제 `azure-foundry` 결과가 하나 이상 있습니다.
4. eval JSON report가 Actions artifact로 남습니다.

임시 배포 cleanup은 테스트 성공 여부와 관계없이 실행되지만 다음 세 조건을 모두 검사합니다.

- 사용자가 cleanup을 명시적으로 켰습니다.
- 실제 테스트한 deployment와 삭제 대상이 같습니다.
- deployment 이름이 `ci-`로 시작합니다.

삭제 명령은 Microsoft가 문서화한 `az cognitiveservices account deployment delete`를 사용합니다. 기존 `FOUNDRY_MODEL` 배포는 기본 설정으로 절대 삭제하지 않습니다. 배포 생성과 삭제 방법은 [Foundry model deployment CLI 문서](https://learn.microsoft.com/azure/foundry/foundry-models/how-to/create-model-deployments)를 참고하세요.

CLI로 수동 실행하려면 다음처럼 dispatch할 수 있습니다.

```bash
gh workflow run foundry-live.yml

# 임시 배포를 테스트하고 종료 시 삭제
gh workflow run foundry-live.yml \
  -f deployment=ci-pronunciation-mapper-test \
  -f cleanup_temporary_deployment=true
```
