# Dependency Injection อธิบายแบบง่ายๆ

## เริ่มจากปัญหาก่อน

ลองนึกถึงพัดลม ถ้าพัดลมต้อง "ผลิตไฟเอง" มันต้องมีเครื่องปั่นไฟติดอยู่ข้างใน — เปลี่ยนแหล่งไฟไม่ได้ ทดสอบก็ยาก แต่ของจริงพัดลมแค่มี**ปลั๊ก** แล้วรอให้ใครสักคนเสียบไฟให้

DI คือแนวคิดเดียวกันในโค้ด: **คลาสไม่ต้องไปหา/สร้างของที่ตัวเองต้องใช้เอง แต่ให้คนข้างนอกยื่นให้ทาง constructor**

## โค้ดแบบไม่มี DI

```csharp
public class OrderService
{
    private readonly EmailSender _sender = new EmailSender();  // ผูกตายตรงนี้

    public void PlaceOrder(Order order)
    {
        // ...บันทึก order...
        _sender.Send(order.CustomerEmail, "สั่งซื้อสำเร็จ");
    }
}
```

ดูเผินๆ ไม่เห็นมีอะไรผิด แต่ลองถามน้องดู 3 คำถามนี้:

1. จะเขียน unit test ยังไงโดยไม่ส่งอีเมลจริง? → ไม่ได้ เพราะ `new` ไปแล้ว
2. วันหนึ่งลูกค้าอยากได้ LINE แทนอีเมล จะทำยังไง? → ต้องแก้ข้างใน `OrderService`
3. ถ้า `EmailSender` ต้องการ SMTP config จะเอามาจากไหน? → `OrderService` ต้องรู้เรื่องที่ไม่ใช่หน้าที่ตัวเอง

ปัญหาคือ `OrderService` มีหน้าที่ "จัดการคำสั่งซื้อ" แต่ดันต้องรู้วิธี**สร้าง**ตัวส่งอีเมลด้วย

## โค้ดแบบมี DI

```csharp
public interface INotificationSender
{
    void Send(string to, string message);
}

public class OrderService
{
    private readonly INotificationSender _sender;

    public OrderService(INotificationSender sender)   // รับเข้ามา ไม่สร้างเอง
    {
        _sender = sender;
    }

    public void PlaceOrder(Order order)
    {
        _sender.Send(order.CustomerEmail, "สั่งซื้อสำเร็จ");
    }
}
```

เท่านี้แหละ คือ dependency injection ทั้งหมด — ไม่มีอะไรลึกลับกว่านี้

ตอนนี้ `OrderService` บอกแค่ว่า "ฉันต้องการของที่ส่งข้อความได้" แต่ไม่สนว่าจะเป็นอีเมล LINE หรือ SMS

**เทสง่ายขึ้นทันที:**

```csharp
public class FakeSender : INotificationSender
{
    public List<string> SentTo = new();
    public void Send(string to, string message) => SentTo.Add(to);
}

// ใน test
var fake = new FakeSender();
var service = new OrderService(fake);
service.PlaceOrder(order);
Assert.Contains("x@y.com", fake.SentTo);   // ไม่ส่งอีเมลจริงสักฉบับ
```

## แล้ว DI Container ล่ะ?

จุดนี้น้องมักสับสน — **DI กับ DI Container คนละเรื่องกัน**

DI คือ "รับ dependency เข้ามาทาง constructor" (อย่างข้างบน ไม่ต้องใช้ library อะไรเลย)

DI Container คือเครื่องมือที่มาช่วยประกอบของให้อัตโนมัติ เพราะพอโปรเจกต์ใหญ่ขึ้น การ `new` ต่อกันเป็นทอดๆ ด้วยมือมันเหนื่อย ใน ASP.NET Core ก็แค่ลงทะเบียนไว้:

```csharp
builder.Services.AddScoped<INotificationSender, EmailSender>();
builder.Services.AddScoped<OrderService>();
```

แล้ว framework จะจัดการสร้างให้เองตอน runtime

**Lifetime ที่ต้องรู้:**

| แบบ | อายุ | ใช้กับ |
|---|---|---|
| `Transient` | สร้างใหม่ทุกครั้งที่ขอ | ของเบาๆ ไม่มี state |
| `Scoped` | หนึ่งตัวต่อหนึ่ง HTTP request | service ทั่วไป, DbContext |
| `Singleton` | หนึ่งตัวตลอดอายุแอป | config, cache, ของที่สร้างแพง |

## กับดักที่มือใหม่มักเจอ

**1. Constructor บวม** — ถ้าเห็น constructor รับ 8 ตัว นั่นไม่ใช่ปัญหาของ DI แต่เป็นสัญญาณว่าคลาสนั้นทำงานเยอะเกินไป ควรแตกออก

**2. ฉีด `IServiceProvider` เข้าไปแล้วไป resolve เอาเอง** — อันนี้เรียก service locator เป็น anti-pattern เพราะทำให้มองไม่เห็นว่าคลาสต้องใช้อะไรบ้าง กลับไปมีปัญหาเดิมทุกอย่าง

**3. สร้าง interface ให้ทุกคลาส** — ไม่จำเป็น ถ้าคลาสนั้นมี implementation เดียวตลอดกาลและไม่ต้อง mock ตอนเทส ก็ inject ตัวคลาสตรงๆ ได้เลย อย่าทำเพราะ "เขาทำกัน"

**4. Captive dependency** — เอา `Scoped` ไปใส่ใน `Singleton` จะพังแบบงงๆ เพราะ singleton จะจับ scoped ตัวแรกไว้ตลอดกาล (.NET จะเตือนให้ถ้าเปิด validate scopes)

## สรุปประโยคเดียวให้น้องจำ

> "อย่าไปหาของที่ต้องใช้เอง ให้ประกาศไว้ที่ constructor แล้วรอรับ"

ถ้าน้องเข้าใจแค่นี้ก็ใช้งานได้จริงแล้ว ส่วน container กับ lifetime ค่อยๆ ซึมเองตอนทำงาน

**แบบฝึกหัดที่ดี:** ให้น้องหยิบคลาสที่มี `new` อยู่ข้างในมาสักตัว แล้วลองแก้ให้เขียน unit test ได้โดยไม่แตะ database หรือ external API — จะเห็นประโยชน์ของ DI ด้วยตัวเองเร็วที่สุด
