---
title: IPFS
tags: [network, p2p, ipfs, cid, merkle-dag, libp2p, kademlia, dht, content-addressing, pinning]
updated: 2026-07-25
---

# IPFS

IPFS(InterPlanetary File System)는 파일을 URL이 아니라 내용 자체의 해시로 식별하는 P2P 파일 시스템이다. HTTP가 "어디서 가져오느냐(location addressing)"를 묻는다면, IPFS는 "무엇을 가져오느냐(content addressing)"를 묻는다.

개념은 단순한데 운영에서 생각보다 걸리는 게 많다. 게이트웨이 의존, 핀닝 관리, 가비지 컬렉션, DHT 라우팅 실패 같은 문제들이 실무에서 자주 만나는 것들이다.

---

## CID (Content Identifier)

CID는 IPFS에서 모든 콘텐츠의 주소다. SHA-256 같은 해시 함수로 데이터를 해시하고, 그 결과를 multibase로 인코딩한 문자열이다.

```
bafybeigdyrzt5sfp7udm7hu76uh7y26nf3efuylqabf3oclgtqy55fbzdi
```

이 문자열 자체가 콘텐츠의 지문이다. 같은 내용이면 어느 피어에서 받든 CID가 동일하고, CID가 다르면 내용이 다르다. HTTP URL처럼 서버가 바뀌거나 파일이 수정돼도 주소가 그대로인 문제가 없다.

CID에는 두 버전이 있다. CIDv0은 Base58로 인코딩된 SHA-256 해시로 `Qm`으로 시작한다. CIDv1은 multibase + multicodec + multihash를 조합한 구조로 더 유연하다. 기본은 `baf`로 시작하는 Base32 인코딩이다.

```
CIDv0: QmXoypizjW3WknFiJnKLwHCnL72vedxjQkDDP1mXWo6uco
CIDv1: bafybeigdyrzt5sfp7udm7hu76uh7y26nf3efuylqabf3oclgtqy55fbzdi
```

CIDv0은 암묵적으로 SHA-256과 dag-pb(Protocol Buffers) 형식만 가정한다. CIDv1은 CID 자체에 해시 함수와 코덱 정보가 인코딩돼 있어서, SHA-3을 쓴 CID인지 SHA-256인지 CID만 보고 알 수 있다. 새 프로젝트는 CIDv1을 써야 한다.

```
CIDv1 구조:
<version> <codec>  <multihash>
   1      dag-pb   sha2-256-<해시값>
```

### CID 검증

CID는 그 자체가 검증 수단이다. 피어에서 데이터를 받으면 해시를 다시 계산해 CID와 비교한다. 맞으면 신뢰할 수 없는 피어에서 받아도 데이터가 맞다는 게 증명된다. 중간에 변조가 일어나면 해시가 달라져서 즉시 감지된다.

```javascript
import { CID } from 'multiformats/cid'
import { sha256 } from 'multiformats/hashes/sha2'
import * as dagPB from '@ipld/dag-pb'

async function computeCID(data) {
  const bytes = new TextEncoder().encode(data)
  const hash = await sha256.digest(bytes)
  return CID.create(1, dagPB.code, hash)
}

// 수신한 데이터 검증
async function verifyCID(expectedCID, receivedBytes) {
  const hash = await sha256.digest(receivedBytes)
  const computed = CID.create(1, dagPB.code, hash)
  return computed.toString() === expectedCID.toString()
}
```

---

## Merkle DAG

IPFS는 파일을 단순한 바이트 덩어리로 저장하지 않는다. Merkle DAG(Directed Acyclic Graph) 구조로 쪼개 저장한다. 각 노드는 데이터와 자식 노드들의 CID 링크를 가진다.

```
큰 파일의 DAG 구조:

Root CID (bafybei...)
├── Chunk 1 CID (bafybei...)  ← 256KB
├── Chunk 2 CID (bafybei...)  ← 256KB
└── Chunk 3 CID (bafybei...)  ← 나머지
```

루트 CID는 청크들의 해시로 만든 해시다. 파일 한 바이트가 바뀌어도 해당 청크 CID가 달라지고, 그 청크를 참조하는 부모 노드 CID도 달라지고, 결국 루트 CID가 달라진다. 파일이 바뀌면 CID가 바뀐다는 건 이 Merkle 속성 때문이다.

이 구조의 실용적인 장점은 중복 제거다. 두 파일이 같은 청크를 공유하면 그 청크는 한 번만 저장된다. 100MB 파일에서 1바이트만 고쳐서 올리면, 변경된 청크와 그 경로의 노드들만 새로 생기고 나머지 청크는 그대로 공유된다.

디렉토리도 같은 구조다. 디렉토리 노드는 파일명과 각 항목의 CID를 링크로 담는다.

```
Directory CID (bafybei...)
├── "readme.txt"  → CID (bafybei...)
└── "data" (dir)  → CID (bafybei...)
    ├── "file1.json" → CID (bafybei...)
    └── "file2.json" → CID (bafybei...)
```

디렉토리에 파일 하나가 추가되면 그 디렉토리 노드의 CID가 바뀐다. 파일 내용 자체는 캐시된 채로 구조만 새 CID를 갖는다. IPFS가 불변(immutable) 파일 시스템인 이유가 여기 있다. 기존 CID가 가리키는 데이터는 영원히 같다.

---

## Kademlia DHT 기반 피어 라우팅

IPFS는 Kademlia DHT로 "특정 CID를 가진 피어"를 찾는다. DHT의 기본 원리는 P2P 문서에서 다뤘으므로 IPFS가 어떻게 쓰는지에 집중한다.

IPFS DHT에서 key는 CID의 멀티해시 부분이고, value는 그 CID를 보유하는 피어 목록(Provider Records)이다. 콘텐츠를 올리면 피어가 자신의 ID와 가까운 노드들에 `ADD_PROVIDER` 메시지를 보낸다. 콘텐츠를 찾을 때는 `GET_PROVIDERS`로 DHT를 조회해 보유 피어를 받는다.

라우팅 테이블 구조는 Kademlia 표준과 같다. 256비트 피어 ID, XOR 거리 기반 k-버킷(k=20). 피어가 많을수록 라우팅이 정밀해지지만, 피어 수가 적거나 DHT에서 멀리 떨어진 노드만 남아있으면 조회 홉이 늘어나 느려진다.

DHT 조회 실패의 주된 원인은 두 가지다. 하나는 Provider Record 만료다. 기본적으로 24시간마다 republish하는데, republish 전에 레코드가 만료되면 DHT에서 사라진다. 다른 하나는 피어 처닝이다. 해당 CID를 보유하던 피어들이 모두 오프라인이면 records는 남아있어도 실제 데이터를 못 받는다.

```bash
# DHT에서 직접 provider 조회
ipfs dht findprovs <CID>

# 특정 피어 위치 조회
ipfs dht findpeer <PeerID>

# 연결된 피어 수 확인 (5개 미만이면 라우팅 실패 위험)
ipfs swarm peers | wc -l
```

---

## libp2p 모듈 구조

IPFS의 네트워크 레이어는 libp2p다. IPFS가 libp2p를 쓰는 게 아니라, IPFS가 libp2p 위에 올려진 애플리케이션이다. libp2p는 피어 발견, 전송, 스트림 멀티플렉싱, 보안을 독립적인 모듈로 조립하게 설계됐다.

### Transport

실제 패킷이 오가는 레이어다. TCP, QUIC, WebSocket, WebRTC가 있다. 노드는 여러 transport를 동시에 열 수 있다. 브라우저 피어는 WebSocket이나 WebRTC만 가능하고, 서버 피어는 TCP와 QUIC가 주력이다. QUIC은 TCP의 head-of-line blocking을 피하고 0-RTT 재연결이 되기 때문에 처닝이 잦은 환경에서 TCP보다 빠르다.

### Multiaddr

전송 주소를 표준화한 형식이다.

```
/ip4/192.168.0.1/tcp/4001        ← TCP
/ip4/192.168.0.1/udp/4001/quic  ← QUIC
/dns4/host.example.com/tcp/4001  ← DNS
/ip4/127.0.0.1/tcp/4001/ws       ← WebSocket
```

하나의 피어가 여러 multiaddr를 advertise할 수 있다. 연결하는 쪽은 목록 중 통하는 걸 골라 쓴다.

### Security

모든 연결은 암호화한다. Noise Protocol Framework가 기본이다. TLS 1.3도 지원한다. 핸드셰이크에서 피어 ID 인증이 함께 일어나서, 연결이 맺어지면 상대가 주장하는 피어 ID가 맞는지 검증된다.

### Stream Muxing

하나의 물리 연결 위에 논리 스트림을 여러 개 연다. yamux와 mplex가 주로 쓰인다. 피어와 연결 하나로 DHT 쿼리, 파일 전송, pubsub 메시지를 동시에 주고받는다.

### Peer Discovery

bootstrap, mDNS, DHT random walk, pubsub peer exchange로 새 피어를 찾는다. 서버 노드는 DHT random walk를 주로 쓰고, 로컬 환경에서는 mDNS가 즉시 붙는다.

### Content Routing

DHT 기반으로 어떤 피어가 특정 CID를 가졌는지 찾는다. 앞서 설명한 Kademlia DHT가 이 레이어에 해당한다.

### PubSub

gossipsub 프로토콜로 토픽 기반 메시지 브로드캐스트를 한다. IPNS 레코드 전파, Filecoin 블록 헤더 전파에 쓰인다.

```javascript
import { createLibp2p } from 'libp2p'
import { tcp } from '@libp2p/tcp'
import { noise } from '@chainsafe/libp2p-noise'
import { yamux } from '@chainsafe/libp2p-yamux'
import { bootstrap } from '@libp2p/bootstrap'
import { kadDHT } from '@libp2p/kad-dht'
import { mdns } from '@libp2p/mdns'

const node = await createLibp2p({
  addresses: {
    listen: ['/ip4/0.0.0.0/tcp/0'],
  },
  transports: [tcp()],
  connectionEncrypters: [noise()],
  streamMuxers: [yamux()],
  peerDiscovery: [
    bootstrap({
      list: [
        '/dnsaddr/bootstrap.libp2p.io/p2p/QmNnooDu7bfjPFoTZYxMNLWUQJyrVwtbZg5gBMjTezGAJN',
      ],
    }),
    mdns(),
  ],
  services: {
    // clientMode: true면 DHT 라우팅에만 참여하고 데이터 저장은 안 한다
    dht: kadDHT({ clientMode: false }),
  },
})

await node.start()
console.log('peer ID:', node.peerId.toString())
console.log('listening on:', node.getMultiaddrs().map(a => a.toString()))
```

---

## 실무 트러블슈팅

### 게이트웨이 의존 문제

IPFS 게이트웨이는 HTTP 요청을 IPFS 네트워크로 변환하는 프록시다. `https://ipfs.io/ipfs/<CID>` 같은 URL이 게이트웨이다. 브라우저에서 IPFS 콘텐츠를 보려면 IPFS 노드를 설치하거나 게이트웨이를 거쳐야 하는데, 대부분의 서비스가 편의상 공개 게이트웨이에 의존한다.

문제는 공개 게이트웨이가 중앙화된 신뢰 지점이 된다는 것이다. IPFS는 분산 파일 시스템인데, 모든 접근이 `ipfs.io`나 `cloudflare-ipfs.com`을 거치면 해당 서비스가 다운될 때 전체가 마비된다. 2021~2022년에 ipfs.io가 몇 차례 느려졌을 때 게이트웨이에 의존하던 NFT 마켓플레이스들의 이미지가 깨진 사례가 있었다.

성능도 문제다. 공개 게이트웨이는 처음 요청되는 CID를 DHT로 찾아야 해서 첫 응답이 느리다. 인기 없는 CID는 수십 초가 걸리기도 한다. 미리 캐시된 콘텐츠면 빠르지만, 신규 업로드는 초기 응답 시간을 예측하기 어렵다.

프로덕션에서 게이트웨이 의존을 줄이려면 전용 게이트웨이를 직접 띄우거나 Cloudflare IPFS 게이트웨이 같은 유료 서비스를 쓴다. 전용 게이트웨이는 자기 노드 캐시를 쓰므로 반복 접근이 빠르고, 내가 제공하는 콘텐츠는 항상 게이트웨이 캐시에 있어서 안정적이다. 브라우저용 IPFS 라이트 클라이언트(Helia)를 앱에 임베드해서 게이트웨이 없이 P2P로 직접 받게 하는 방법도 있다.

```javascript
// Helia를 브라우저에 임베드해 게이트웨이 없이 IPFS 접근
import { createHelia } from 'helia'
import { strings } from '@helia/strings'
import { CID } from 'multiformats/cid'

const helia = await createHelia()
const s = strings(helia)

const cid = CID.parse('bafybeigdyrzt5sfp7udm7hu76uh7y26nf3efuylqabf3oclgtqy55fbzdi')
const content = await s.get(cid)
console.log(content)  // 게이트웨이 없이 P2P로 직접 받음
```

### 핀닝 (Pinning)

IPFS 노드는 가져온 데이터를 로컬에 캐시한다. 가비지 컬렉션이 돌면 참조되지 않는 블록은 삭제된다. 내가 올린 파일도 마찬가지다. 핀(Pin)은 특정 CID를 "이건 지우지 마라"고 표시하는 것이다. 핀하지 않은 데이터는 가비지 컬렉션 때 사라진다.

```bash
# 로컬 노드 핀 관리
ipfs pin add <CID>               # 핀 추가 (하위 블록 모두 포함)
ipfs pin rm <CID>                # 핀 제거
ipfs pin ls --type=recursive     # 재귀 핀 목록 확인
```

핀에는 세 종류가 있다. `direct`는 해당 CID 블록만 핀하고 하위 링크는 무시한다. `recursive`는 해당 CID와 참조하는 모든 하위 블록을 핀한다. `indirect`는 recursive 핀의 하위 블록들이 자동으로 받는 상태다. 디렉토리나 파일을 핀할 때는 거의 항상 recursive를 써야 한다.

함정은 노드 하나의 핀은 그 노드에서만 유효하다는 것이다. 노드가 꺼지거나 디스크가 날아가면 핀이고 뭐고 다 사라진다. 영속성이 필요하면 핀닝 서비스(Pinata, web3.storage, nft.storage 등)를 써야 한다. 이 서비스들은 CID를 받아서 자기 노드들에 핀하고 항상 온라인 상태를 유지한다.

```javascript
// Pinata API로 파일 업로드 및 핀닝
import PinataSDK from '@pinata/sdk'
import fs from 'fs'

const pinata = new PinataSDK({ pinataJWT: process.env.PINATA_JWT })

const result = await pinata.pinFileToIPFS(fs.createReadStream('./file.json'), {
  pinataMetadata: { name: 'my-data' },
})
console.log('CID:', result.IpfsHash)
// Pinata가 이 CID를 핀하므로 로컬 노드 없이도 네트워크에서 접근 가능
```

핀닝 서비스를 쓰더라도 여러 서비스에 이중으로 핀하는 게 안전하다. 서비스가 망하거나 약관 위반으로 데이터가 삭제될 위험이 있다. 중요한 데이터라면 Pinata와 Filecoin(장기 보관 계약)을 병행하는 식으로 레이어를 두는 게 현실적이다.

### 가비지 컬렉션 (Garbage Collection)

IPFS 노드는 데이터를 계속 받다 보면 디스크가 꽉 찬다. 가비지 컬렉션은 핀되지 않은 블록을 지워 공간을 회수한다.

```bash
# GC 전 상태 확인
ipfs repo stat

# 수동 GC 실행
ipfs repo gc
```

기본값으로 GC는 수동 실행이다. 자동 GC는 설정으로 켤 수 있다.

```json
// ~/.ipfs/config
{
  "Datastore": {
    "StorageMax": "10GB",
    "StorageGCWatermark": 90,
    "GCPeriod": "1h"
  }
}
```

`StorageGCWatermark`가 90이면 `StorageMax`의 90%에 도달할 때 GC를 트리거한다.

자동 GC를 켜 두면 핀 안 한 중요 데이터가 날아가는 일이 생긴다. 처음 IPFS를 쓰는 사람들이 가장 많이 하는 실수다. "노드에 올렸으니까 있겠지"라고 생각하고 핀을 안 했다가 GC 후 데이터가 사라진다. IPFS에 올리는 모든 데이터는 올리자마자 핀하거나 핀닝 서비스에 CID를 등록하는 걸 루틴으로 만들어야 한다.

GC 실행 시간도 주의해야 한다. 블록이 수백만 개 쌓여 있으면 GC가 수분 이상 걸리고, 그 동안 노드 응답이 느려진다. 운영 노드에서는 GC를 트래픽이 적은 시간대로 스케줄링하거나, GC 시간을 짧게 유지하려면 주기적으로 불필요한 CID 핀을 제거해야 한다.

### DHT 라우팅 실패

올린 파일이 DHT에서 안 잡히는 경우가 있다. Provider Records는 올릴 때 DHT에 publish되는데, 이 과정이 비동기라 `ipfs add`가 끝나도 DHT에 레코드가 퍼질 때까지 시간이 걸린다. 노드가 DHT에 막 합류했거나 라우팅 테이블이 얇을 때 더 심하다.

피어 수가 너무 적으면(5개 미만이면 거의 확실히) DHT 조회 홉이 많아지고 실패율이 올라간다. bootstrap 노드에 접근이 안 되거나 방화벽이 4001 포트를 막으면 피어를 못 모은다.

방화벽 문제는 흔하다. IPFS 기본 포트는 4001(TCP/UDP)인데, 이 포트가 막혀 있으면 외부 피어가 들어오지 못하고 나가는 연결만 가능한 반-연결 상태가 된다. 이런 노드는 DHT에서 provider로 광고돼도 외부 피어가 연결을 못 맺어서 데이터를 못 받는다.

```bash
# 외부에서 내 노드에 접근 가능한지 확인
ipfs id  # multiaddr 목록 확인

# /ip4/<공인IP>/tcp/4001 형식 주소가 없으면 외부 접근 불가
# NAT 환경이면 포트 포워딩이나 AutoNAT/AutoRelay 설정 필요
```

AutoRelay를 켜두면 NAT 뒤에 있어도 relay 피어를 찾아 외부에서 접근 가능한 주소를 자동으로 확보한다. 기본 IPFS 설정에서는 꺼져 있다.

```json
// ~/.ipfs/config
{
  "Swarm": {
    "EnableAutoRelay": true,
    "RelayClient": {
      "Enabled": true
    }
  }
}
```

### 콘텐츠 불변성과 업데이트 문제

CID가 불변이라는 건 내용이 바뀌면 CID도 바뀐다는 뜻이다. "최신 버전"을 가리키는 고정 주소가 없다. 이걸 해결하는 게 IPNS(InterPlanetary Name System)다. IPNS는 피어 ID를 키로 쓰는 가변 포인터다. IPNS 레코드를 갱신하면 같은 IPNS 주소가 새 CID를 가리키게 된다.

```bash
ipfs name publish <CID>                  # 내 피어 ID의 IPNS 레코드를 <CID>로 갱신
ipfs name resolve /ipns/<PeerID>         # IPNS 주소로 현재 CID 조회
```

IPNS의 단점은 조회가 느리다는 것이다. DHT에서 IPNS 레코드를 찾아야 하므로 HTTP URL 조회와 비교도 안 되게 느리다. 개선책으로 DNSLink를 쓰는 경우가 많다. DNS TXT 레코드에 `/ipfs/<CID>`를 박아두면 도메인 이름으로 IPFS 콘텐츠를 접근할 수 있다. DNS TTL로 캐시되고 DNS 조회는 빠르다.

```
_dnslink.example.com.  TXT  "dnslink=/ipfs/bafybei..."
```

```bash
ipfs resolve /ipns/example.com  # DNS TXT를 거쳐 CID 조회
```

콘텐츠를 자주 갱신해야 하는 서비스라면 IPFS를 저장소로 쓰고 최신 CID를 가리키는 포인터는 전통적인 데이터베이스나 스마트 컨트랙트에 두는 패턴이 현실적이다. IPNS나 DNSLink는 갱신 주기가 수십 분 이상인 콘텐츠에 적합하다.
