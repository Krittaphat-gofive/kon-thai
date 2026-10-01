อธิบายสั้นที่สุดคือ "คลาสไม่ต้องหาของใช้เอง ให้คนอื่นส่งเข้ามาให้" ครับ

เปรียบเทียบง่าย ๆ เหมือนครัวร้านอาหาร เชฟไม่ต้องไปปลูกผักเอง มีคนเตรียมวัตถุดิบมาวางให้ถึงมือ เชฟมีหน้าที่ทำอาหารอย่างเดียว DI ก็แบบนั้น คลาสไหนต้องใช้อะไรก็ประกาศไว้ที่ constructor แล้วรอรับ

## ปัญหาที่ DI มาแก้

ลองดูโค้ดแบบที่ยังไม่ใช้ DI

```csharp
public class OrderService
{
    private readonly SqlOrderRepository _repo = new SqlOrderRepository();

    public void Place(Order order)
    {
        _repo.Save(order);
    }
}
```

ตรง `new SqlOrderRepository()` นี่แหละคือตัวปัญหา เพราะ `OrderService` ผูกกับ `SqlOrderRepository` แบบแกะไม่ออก ผลที่ตามมาคือ

- เขียน unit test ไม่ได้ เพราะทุกครั้งที่เทสจะวิ่งไปต่อ database จริง
- วันไหนอยากเปลี่ยนไปใช้ที่เก็บแบบอื่น ต้องเข้าไปแก้ในคลาสนี้
- ถ้า `SqlOrderRepository` ต้องการ connection string เพิ่ม `OrderService` ก็ต้องรู้เรื่องนั้นไปด้วยทั้งที่ไม่ใช่หน้าที่

## ทำเป็น DI

```csharp
public class OrderService
{
    private readonly IOrderRepository _repo;

    public OrderService(IOrderRepository repo)
    {
        _repo = repo;
    }

    public void Place(Order order)
    {
        _repo.Save(order);
    }
}
```

เปลี่ยนแค่นี้เอง จาก new เองกลายเป็นรับเข้ามาทาง constructor ทีนี้ `OrderService` รู้แค่ว่า "มีของที่ save order ได้" ส่วนของจริงจะเป็นตัวไหนไม่สนใจแล้ว

เวลาเทสก็ส่งตัวปลอมเข้าไปได้เลย

```csharp
var service = new OrderService(new FakeOrderRepository());
```

## แล้วใครเป็นคนส่งของเข้ามา

ตอน run จริงคนส่งคือ DI container ซึ่งใน .NET มีมาให้ในตัว เราแค่ไปบอกไว้ที่เดียวว่าของแต่ละอย่างหน้าตายังไง

```csharp
builder.Services.AddScoped<IOrderRepository, SqlOrderRepository>();
builder.Services.AddScoped<OrderService>();
```

พอมีคนขอ `OrderService` container จะเห็นว่า constructor ต้องใช้ `IOrderRepository` ก็ไปหยิบ `SqlOrderRepository` มาสร้างให้อัตโนมัติ ไล่ลงไปเรื่อย ๆ จนครบทั้งสาย

จุดนี้น้องมักสับสน เลยอยากย้ำ: DI คือแนวคิดการส่งของเข้ามาทาง constructor ส่วน container เป็นแค่ตัวช่วยประกอบให้ ไม่มี container ก็ทำ DI ได้ แค่ต้อง new เองที่จุดเริ่มโปรแกรม

## lifetime ที่ต้องรู้ไว้

ตอนลงทะเบียนจะมีสามแบบให้เลือก เรื่องนี้ชนบ่อยมาก

| แบบ | สร้างใหม่เมื่อไหร่ | เหมาะกับ |
|---|---|---|
| Transient | ทุกครั้งที่มีคนขอ | ของเบา ๆ ที่ไม่เก็บ state |
| Scoped | ครั้งเดียวต่อหนึ่ง request | DbContext, repository |
| Singleton | ครั้งเดียวตลอดอายุแอป | config, cache |

กฎเหล็กข้อเดียวที่ต้องจำคือ อย่าเอา scoped ไปยัดใน singleton เช่น singleton ที่รับ `DbContext` เข้ามา เพราะ context ตัวนั้นจะค้างอยู่ตลอดอายุแอปแทนที่จะจบไปพร้อม request แล้วจะเจอ error แปลก ๆ ตอน production

## สรุปให้น้องจำ

เห็น `new` อยู่ในคลาสที่มี business logic เมื่อไหร่ ให้สงสัยไว้ก่อนว่าควรดึงออกมาเป็น constructor parameter ไหม ยกเว้นพวก object ข้อมูลล้วน ๆ อย่าง DTO หรือ model พวกนั้น new ได้ตามปกติ

ถ้าทีมใช้ Angular หรือ TypeScript เดี๋ยวผมเขียนตัวอย่างชุดเดียวกันให้ใหม่ได้ครับ แนวคิดเหมือนกันเป๊ะ ต่างแค่ syntax
