# Comparing Apache Kafka and NATS JetStream: A Technical Deep Dive

This technical discussion compares Apache Kafka and NATS (with JetStream) as solutions for distributed computing, focusing on their fundamental architectural differences rather than performance benchmarks. Engineers evaluating message streaming platforms for low-latency messaging, event processing, or distributed data storage will find valuable insights into how these technologies approach similar problems with distinctly different design philosophies.

## What This Documentation Covers

This document examines the core architectural and functional differences between Apache Kafka and NATS JetStream, two popular technologies for distributed messaging and stream processing. The discussion focuses on subject-based addressing, data storage models, partitioning strategies, and the trade-offs between throughput and latency.

## Why This Matters

Understanding the fundamental differences between Kafka and NATS is critical for:

* **System Architects** designing distributed systems who need to choose between streaming platforms based on actual requirements rather than popularity
* **Engineers** working with event-driven architectures who need real-time messaging versus high-throughput batch processing
* **Organizations** evaluating migration paths from Kafka to NATS or making initial platform decisions
* **Developers** building applications that require fine-grained message addressing, data compliance requirements, or low-latency operations

## Historical Context and Design Philosophy

### Apache Kafka: The Distributed Log

Kafka was designed from inception as a **distributed log processing platform**. While it can be adapted for messaging use cases, its core design centers on streaming and semi-real-time (not real-real-time) log processing. Kafka excels at ingesting massive volumes of data that will be temporarily stored before distribution to data lakes or analytics platforms.

Key characteristics:

* Streaming-first architecture
* Optimized for throughput over latency
* Measures latencies in milliseconds
* Uses extensive batching for performance

### NATS: Messaging with Persistence

NATS originated as a **low-latency, high-throughput messaging system** implementing publish-subscribe with subject-based addressing, proper request-reply patterns, and true message queuing. The JetStream persistence layer was added later, giving NATS streaming processing functionality comparable to Kafka while maintaining its messaging foundations.

Key characteristics:

* Messaging-first architecture with streaming capabilities layered on top
* Optimized for latency with optional throughput optimization
* Measures latencies in microseconds (sub-100 microseconds on fast networks)
* Supports both real-time and batched operations

## First Fundamental Difference: Subject-Based Addressing

### Kafka's Topic-Based Model

In Kafka, a **topic** is essentially a string identifier. While Kafka supports regex matching against topic names, clients must continuously poll and refresh their list of known topics to discover new matches. Critically:

* One topic equals one stream
* One topic typically contains one subject
* Topics have no hierarchical structure
* Messages are addressed only by **offset** (partition number + sequence number)

#### The Key Field Limitation

Kafka provides a "key" field when publishing messages, but this key serves **exactly one purpose**: determining which partition the message will be hashed to. The key cannot be used to:

* Address individual messages
* Query for messages with specific key values
* Filter messages server-side

### NATS JetStream's Subject-Based Addressing

JetStream implements **hierarchical subject-based addressing** where subjects are multi-part strings with dot-separated tokens. This creates a powerful indexing and querying mechanism.

#### Subject Structure and Wildcards

Subjects follow a pattern like: `orders.region.customerID`

Two types of wildcards enable flexible querying:

* **`*` (partial wildcard)**: Matches any value for that specific token position
* **`>` (trailing wildcard)**: Matches one or more tokens after this point

Examples:

* `foo.bar.*.>` matches `foo.bar.x.y` and `foo.bar.x.y.z`
* `foo.bar.*.>` does NOT match `foo.bar.x` (missing trailing tokens)
* `orders.us.*` retrieves all US orders
* `sensor.temperature.*.*` retrieves all temperature sensor data

#### Direct Message Addressing

JetStream allows you to address individual messages or message series directly within the stream:

* **Get operations**: Retrieve first/last message for a specific subject
* **Simple queries**: Use wildcards to match message subsets
* **Server-side filtering**: Only matching messages are transmitted to clients
* **Internal indexing**: JetStream maintains indexes on subject names for fast retrieval

#### Practical Example: Market Data

Consider a NASDAQ topic with 100,000 different instruments:

**Kafka approach:**

* Create topic `nasdaq.[instrument]` with instrument name as key
* To get only Microsoft (MSFT) updates: broker sends ALL messages to client/process
* Client must inspect each message's key and discard non-matching messages
* Extremely inefficient: transfers all data over network, discards most of it

**NATS approach:**

* Create stream capturing `nasdaq.*`
* Subject pattern: `nasdaq.msft`, `nasdaq.ibm`, etc.
* Query `nasdaq.msft` directly using subject-based indexing
* Server performs filtering and transmits only matching messages
* Client receives exactly what it needs

### Consumers and Consumer Groups

Terminology differs between platforms:

**Kafka terminology:**

* Consumer groups contain multiple consumers (client applications)
* Consumers must manage their own offset state
* No built-in state management

**NATS terminology:**

* **Consumers** (equivalent to Kafka consumer groups) can be shared by multiple client applications
* Messages are distributed among subscribing client applications
* Consumers maintain state on the server (acknowledged messages, current position)
* Clients are completely stateless
* Consumers function like database "views" on streams with optional filters

### Partitioning Philosophy

**Kafka:**

* Designed around the assumption of one client application per topic at a time
* **Requires partitions** to distribute messages among multiple consuming clients
* Partitions are hard-coded architectural elements
* Distribution is mandatory for horizontal scaling

**NATS:**

* **Partitionless by default**
* Can artificially create partitions if needed using subject tokens
* Uses subject-based consistent hashing to insert partition numbers into subjects
* Example: `foo.aa` → partition 1, `foo.baz` → partition 2
* Maintains deterministic routing like Kafka when partitioning is desired

## Second Fundamental Difference: Data Storage

### Kafka: The Write-Ahead Log

Kafka implements a **write-ahead log (WAL)** as its core storage mechanism. This design choice has significant implications:

**Capabilities:**

* Append messages to the head of the log
* Tail compaction to drop old messages
* Keep at least one message with a particular key value (during compaction)

**Limitations:**

* **No individual message deletion**
* No concept of rejecting writes (except when stream is full)
* No constraints or limits per key
* No concurrency access control
* Designed to always accept writes when space available

**Use case optimization:**
Kafka excels at accepting high-volume incoming data that will be:

* Temporarily stored in Kafka
* Quickly distributed to data lakes or analytics platforms
* Processed in batch rather than individually

### NATS JetStream: The Data Store

JetStream functions more like a **NoSQL database** with full data store capabilities:

#### CRUD Operations

**Create/Insert:**

* Publish message only if no message exists at that subject
* Returns failure if message already exists

**Read:**

* Get operations by subject
* Query ranges using wildcards
* Direct indexed access

**Update:**

* Compare-and-set operation
* Specify expected current message sequence number
* Operation fails if message has changed
* Prevents data race conditions and blind overwrites

**Delete:**

* Delete individual messages by subject
* Not limited to tail compaction

**Upsert:**

* Default Kafka-like behavior
* Insert if nothing exists, overwrite if something exists
* Available when concurrency control is not needed

#### Advanced Constraints and Limits

**Per-subject limits:**

* Maximum number of messages per subject (e.g., exactly 4 messages for `orders.12345`)
* Unlike Kafka's "at least one" during compaction, JetStream enforces "exactly N"
* Enables use cases like distributed locking and logic gating

**Discard policies:**
When limits are hit, two options:

1. **Delete old messages** to make room (stay within limit)
2. **Reject the write** and return failure (enforce constraint)

**Use case example - Distributed Locking:**

* Set limit of one message per subject
* First write succeeds and "acquires lock"
* Subsequent writes to same subject fail with "limit reached"
* Lock released by deleting the message

#### Rollup Operations

Rollups provide atomic message consolidation:

* Take multiple messages on a subject
* Replace them with a single aggregated message
* Example: Multiple order adjustments (+$20, -$10, +$5) rolled up into single net change (+$15)
* Single atomic operation
* No equivalent in Kafka

#### Higher-Level Abstractions

The combination of subject-based addressing, constraints, CRUD operations, and limits enables:

* **Key-Value Store**: Using streams with one-message-per-subject limits
* **Object Store**: Storing larger blobs with subject-based organization
* **Last-Value Cache**: Keeping only the N most recent messages per subject

### Data Storage Comparison Summary

| Feature             | Kafka                     | NATS JetStream                       |
|---------------------|---------------------------|--------------------------------------|
| Storage Model       | Write-ahead log           | Data store / NoSQL database          |
| Individual Deletes  | No                        | Yes                                  |
| Write Rejection     | Only when full            | Configurable via discard policy      |
| Per-Key Limits      | At least one (compaction) | Exactly N (enforced)                 |
| Concurrency Control | None                      | Compare-and-set operations           |
| Update Operations   | Append only               | Insert, Update, Upsert, Delete       |
| Constraints         | None                      | Per-subject limits, discard policies |
| Rollups             | No                        | Yes                                  |

## Positives and Negatives

### Apache Kafka Strengths

* **Proven horizontal scalability** for write-heavy workloads
* **Exceptional throughput** for high-volume event ingestion (millions of events/second)
* **Mature ecosystem** with extensive tooling and integrations
* **Battle-tested** in production at massive scale
* **Simple write path** optimized for performance

### Apache Kafka Limitations

* **Not designed for low latency** (millisecond range, not microsecond)
* **Limited message addressing** (offset-based only)
* **No server-side filtering** by message content
* **Requires partitions** for horizontal distribution
* **No individual message deletion** or updates
* **No built-in concurrency control** for writes
* **Clients must manage state** for consumer groups
* **Inefficient for selective data retrieval** (must transfer and filter client-side)

### NATS JetStream Strengths

* **True low-latency messaging** (sub-100 microsecond capable)
* **Flexible subject-based addressing** with hierarchical indexing
* **Server-side filtering** reduces network traffic
* **Stateless clients** (server maintains consumer state)
* **Partitionless by default** with optional partitioning
* **Full CRUD operations** with concurrency control
* **Data compliance capabilities** via individual message deletion
* **Multi-purpose** (messaging, streaming, KV store, object store)
* **Flexible limits and constraints** per subject or stream-wide

### NATS JetStream Limitations

* **May not match Kafka's peak throughput** for pure write-heavy workloads (though batching helps)
* **Newer streaming implementation** compared to Kafka's maturity
* **Less extensive ecosystem** than Kafka (though growing rapidly)
* **More complex mental model** for developers familiar only with simple pub-sub

### Risk Considerations

**Kafka Risks:**

* **Over-engineering**: Using Kafka when simpler messaging would suffice
* **Hidden complexity**: Partition management, rebalancing, and offset tracking add operational overhead
* **Client-side filtering waste**: Network and CPU resources spent on discarded messages
* **Limited flexibility**: Difficult to add new access patterns after initial design

**NATS Risks:**

* **Underestimating requirements**: May need to implement batching for very high throughput scenarios
* **Subject design**: Poor subject hierarchy design can limit future flexibility
* **Resource planning**: More sophisticated features require understanding of limit and constraint interactions

## Key Learnings

1. **Choose based on actual requirements**: Kafka excels at high-volume log ingestion with eventual processing; NATS excels at flexible real-time messaging with data store capabilities.

2. **Latency vs. Throughput is a real trade-off**: Batching improves throughput but increases latency. Know which your application truly needs.

3. **Subject design matters in NATS**: Invest time in designing hierarchical subject taxonomies that support current and future access patterns.

4. **Partitioning philosophy differs fundamentally**: Kafka requires partitions; NATS makes them optional. Understand the implications for your scaling strategy.

5. **Data lifecycle requirements**: If you need individual message deletion (compliance, GDPR), data constraints, or concurrency control, JetStream provides these natively.

6. **Client complexity varies**: Kafka pushes state management and filtering to clients; NATS handles these server-side, simplifying client applications.

## Further Information

* [Apache Kafka Documentation](https://kafka.apache.org/documentation/) - Official Kafka architecture and design documentation
* [NATS JetStream Documentation](https://docs.nats.io/nats-concepts/jetstream) - JetStream concepts and capabilities
* [Subject-Based Messaging](https://docs.nats.io/nats-concepts/subjects) - Deep dive into NATS subject design patterns
* [Kafka Streams](https://kafka.apache.org/documentation/streams/) - Kafka's stream processing library
* [NATS Consumer Types](https://docs.nats.io/nats-concepts/jetstream/consumers) - Understanding JetStream consumers and their configurations
* [Distributed Messaging Patterns](https://www.enterpriseintegrationpatterns.com/) - General messaging architecture patterns applicable to both systems
* [CAP Theorem in Distributed Systems](https://en.wikipedia.org/wiki/CAP_theorem) - Understanding trade-offs in distributed data stores
* [Event Sourcing](https://martinfowler.com/eaaDev/EventSourcing.html) - Pattern commonly implemented with both Kafka and NATS
