## สรุปประโยคเดียวก่อน

**Dependency Injection คือ "อย่าไปหาของที่ต้องใช้เอง ให้คนอื่นส่งมาให้"**

---

## อุปมาแบบเห็นภาพ

ลองนึกถึงเชฟสองแบบ:

- **เชฟแบบ A**: จะทำผัดกะเพรา ต้องเดินไปตลาดเอง เลือกร้าน ซื้อหมู ซื้อใบกะเพราเอง → ถ้าอยากให้เขาลองทำด้วยเนื้อแทนหมู ต้องไปแก้โค้ดข้างในหัวเขา และถ้าอยากทดสอบว่าเขาผัดเป็นไหม ก็ต้องให้เขาเดินไปตลาดจริงๆ ทุกครั้ง
- **เชฟแบบ B**: บอกว่า "ส่งเนื้อสัตว์กับผักมาให้ผม แล้วผมผัดให้" → อยากได้เมนูเนื้อก็ส่งเนื้อมา อยากทดสอบก็ส่งของปลอมมาได้

เชฟแบบ B คือ Dependency Injection ครับ

---

## โค้ดจริง — แบบที่ยังไม่มี DI

```csharp
public class OrderService
{
    private readonly SqlOrderRepository _repo = new SqlOrderRepository();
    private readonly SmtpEmailSender _email = new SmtpEmailSender();

    public void PlaceOrder(Order order)
    {
        _repo.Save(order);
        _email.Send(order.CustomerEmail, "สั่งซื้อสำเร็จ");
    }
}
```

ดูเผินๆ ไม่เห็นมีอะไรผิด แต่ปัญหาคือ:

1. **เขียนเทสต์ไม่ได้** — เรียก `PlaceOrder` ทีไร ต่อ DB จริงและยิงอีเมลจริงทุกครั้ง
2. **เปลี่ยนของไม่ได้** — วันหนึ่งย้ายจาก SQL ไป MongoDB หรือเปลี่ยนจาก SMTP ไป SendGrid ต้องเข้ามาแก้ `OrderService` ทั้งที่ logic การสั่งซื้อไม่ได้เปลี่ยนเลย
3. **`OrderService` รู้มากเกินไป** — มันควรรู้แค่ "ขั้นตอนการสั่งซื้อ" ไม่ใช่ "ต้องต่อ DB ยังไง"

---

## โค้ดเดิม แบบมี DI

```csharp
public class OrderService
{
    private readonly IOrderRepository _repo;
    private readonly IEmailSender _email;

    // ของที่ต้องใช้ รับเข้ามาทาง constructor
    public OrderService(IOrderRepository repo, IEmailSender email)
    {
        _repo = repo;
        _email = email;
    }

    public void PlaceOrder(Order order)
    {
        _repo.Save(order);
        _email.Send(order.CustomerEmail, "สั่งซื้อสำเร็จ");
    }
}
```

เปลี่ยนแค่สองอย่าง:
- พึ่งพา **interface** (`IOrderRepository`) แทนคลาสจริง (`SqlOrderRepository`)
- **รับเข้ามาทาง constructor** แทนการ `new` เอง

ทีนี้เทสต์ง่ายมาก:

```csharp
var service = new OrderService(new FakeOrderRepository(), new FakeEmailSender());
service.PlaceOrder(order);
// ไม่แตะ DB ไม่ส่งอีเมลจริง รันเร็วเป็นมิลลิวินาที
```

---

## แล้ว "DI Container" คืออะไร?

พอทำแบบนี้ไปเรื่อยๆ จะเจอปัญหาใหม่ — ใครเป็นคน `new` ให้?

```csharp
var service = new OrderService(
    new SqlOrderRepository(new DbConnection(connStr)),
    new SmtpEmailSender(new SmtpConfig(...)));
```

เขียนเองก็ได้ แต่พอโปรเจกต์ใหญ่ขึ้นจะเริ่มเหนื่อย DI Container เลยเข้ามาช่วย เราแค่ **ลงทะเบียน**ไว้ว่าเจอ interface ตัวไหนให้หยิบคลาสไหนมาใช้ ที่เหลือมันประกอบให้เอง:

```csharp
builder.Services.AddScoped<IOrderRepository, SqlOrderRepository>();
builder.Services.AddScoped<IEmailSender, SmtpEmailSender>();
builder.Services.AddScoped<OrderService>();
```

จุดที่น้องใหม่มักสับสน: **DI กับ DI Container ไม่ใช่สิ่งเดียวกัน** — DI คือ *แนวคิด* (รับของเข้ามาแทนที่จะหาเอง) ส่วน Container เป็นแค่ *เครื่องมือ* ที่ช่วยทำให้สะดวก ไม่มี Container ก็ทำ DI ได้

---

## Lifetime — เรื่องที่ต้องรู้เพิ่มถ้าใช้ Container

ตอนลงทะเบียนจะต้องบอกว่าอยากให้ object อยู่นานแค่ไหน:

| แบบ | ความหมาย | ใช้เมื่อไหร่ |
|---|---|---|
| `Transient` | สร้างใหม่ทุกครั้งที่ขอ | object เบาๆ ไม่มี state |
| `Scoped` | ตัวเดียวต่อ 1 request | ส่วนใหญ่ใช้อันนี้ เช่น DbContext, Repository |
| `Singleton` | ตัวเดียวตลอดอายุแอป | config, cache, ของที่ thread-safe |

**กับดักคลาสสิก**: อย่าเอา Scoped ไปยัดใน Singleton (เช่น Singleton ที่ inject `DbContext` เข้าไป) — มันจะค้างอยู่ตลอดอายุแอปและพังแบบหาสาเหตุยากมาก

---

## ข้อควรระวังที่อยากให้น้องรู้ตั้งแต่แรก

**1. ไม่ใช่ทุกอย่างต้อง inject** — คลาสที่ไม่มี side effect อย่าง `DateTime`, `StringBuilder`, value object ต่างๆ `new` ตรงๆ ได้เลย ให้ inject เฉพาะของที่แตะโลกภายนอก (DB, API, ไฟล์, เวลา, random) หรือของที่อยากสลับไส้ในได้

**2. ถ้า constructor มีพารามิเตอร์ 8-10 ตัว นั่นไม่ใช่ปัญหาของ DI** — มันคือสัญญาณว่าคลาสนั้นทำงานเยอะเกินไป ควรแตกออก DI แค่ทำให้ปัญหาที่ซ่อนอยู่มองเห็นได้ชัดขึ้นเท่านั้น

**3. อย่าใช้ Service Locator** — คือการ inject ตัว container เข้ามาแล้วไปขอของเอาเองข้างใน:

```csharp
// อย่าทำ
public OrderService(IServiceProvider sp) { _sp = sp; }
public void PlaceOrder(Order o) { var repo = _sp.GetService<IOrderRepository>(); }
```

แบบนี้ซ่อน dependency ไว้ข้างใน มองจาก constructor ไม่รู้เลยว่าคลาสนี้ต้องใช้อะไรบ้าง — เสียประโยชน์หลักของ DI ไปเกือบหมด

---

## วิธีอธิบายให้น้องจำได้

ลองให้น้องถามตัวเอง 2 คำถามนี้ทุกครั้งที่จะเขียน `new` ในคลาส:

1. "ของชิ้นนี้ตอนเขียนเทสต์ ฉันอยากสลับเป็นของปลอมไหม?"
2. "ของชิ้นนี้มีโอกาสเปลี่ยนไส้ในไหม?"

ถ้าตอบ "ใช่" ข้อใดข้อหนึ่ง → รับเข้ามาทาง constructor ครับ
