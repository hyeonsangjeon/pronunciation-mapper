# PyPI 릴리스 운영

Pronunciation Mapper는 PyPI API token이나 계정 password를 GitHub에 저장하지 않습니다. GitHub Actions가 OpenID Connect(OIDC) identity를 발급받고 PyPI Trusted Publisher가 저장소, workflow와 Environment를 검증한 뒤에만 업로드를 허용합니다.

## 고정된 게시 identity

| 항목 | 값 |
| --- | --- |
| PyPI project | `pronunciation-mapper` |
| GitHub owner | `hyeonsangjeon` |
| GitHub repository | `pronunciation-mapper` |
| Workflow | `pypi-publish.yml` |
| GitHub Environment | `pypi` |

PyPI의 publisher 설정과 [publish workflow](../.github/workflows/pypi-publish.yml)의 파일명·Environment가 정확히 일치해야 합니다.

첫 실행 전에 GitHub repository에 `pypi` Environment를 명시적으로 만들고 custom deployment policy를 다음처럼 제한합니다.

- branch: `main`
- tag: `v*`

Environment에는 PyPI password나 API token을 저장하지 않습니다. 여러 maintainer가 있는 repository라면 required reviewer도 추가합니다.

## 첫 게시

프로젝트가 아직 PyPI에 없을 때 계정의 **Publishing → Add a new pending publisher**에서 위 identity를 등록합니다. Pending Publisher는 이름을 예약하지 않으며, 처음 성공한 trusted publish가 프로젝트를 생성하면서 일반 publisher로 전환합니다.

이미 생성된 `v2.0.0`을 처음 게시할 때는 workflow가 `main`에 merge된 후 다음처럼 실행합니다.

```bash
gh workflow run pypi-publish.yml --ref main -f tag=v2.0.0
gh run list --workflow pypi-publish.yml --limit 1
```

Workflow는 요청한 tag를 checkout하고 `pyproject.toml`의 version과 tag가 일치하는지 확인합니다. 이미 게시된 동일 version은 덮어쓰지 않습니다.

## 이후 릴리스

1. CHANGELOG와 release record를 새 version으로 마감합니다.
2. `main` CI를 통과한 commit에 annotated tag를 생성합니다.
3. 같은 tag로 GitHub Release를 게시합니다.
4. `release.published` event가 PyPI workflow를 자동 실행하는지 확인합니다.
5. PyPI project page, wheel/sdist, provenance와 새 환경 설치를 검증합니다.

GitHub prerelease는 자동 게시하지 않습니다. 수동 dispatch는 기존 stable tag의 첫 게시나 자동 workflow 복구에만 사용합니다.

## 보안 경계

- Build job에는 `id-token: write`가 없고 source checkout과 build만 수행합니다.
- Publish job은 build artifact만 받아 실행하며 source code나 build script를 실행하지 않습니다.
- Publish job만 `pypi` Environment와 `id-token: write`를 사용합니다.
- `pypi` Environment는 `main` branch와 `v*` tag deployment만 허용합니다.
- 모든 외부 action은 immutable commit SHA로 고정합니다.
- Workflow는 실제 annotated tag를 checkout했는지, tag가 가리키는 commit이 `HEAD`인지, 그 commit이 `main` 이력에 포함되는지 검증합니다.
- Trusted Publishing에서는 Sigstore 기반 PyPI digital attestation이 기본 생성됩니다.
- API token이나 account password를 repository secret으로 추가하지 않습니다.

PyPI version과 distribution filename은 재사용할 수 없습니다. 잘못된 릴리스는 같은 version을 덮어쓰지 말고 필요하면 yank한 뒤 patch version으로 수정합니다.
