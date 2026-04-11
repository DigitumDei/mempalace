use serde::{Serialize, Deserialize};
use time::OffsetDateTime;

#[derive(Serialize)]
struct Test {
    t: OffsetDateTime,
}

fn main() {
    let t = OffsetDateTime::now_utc();
    let test = Test { t };
    println!("{}", serde_json::to_string(&test).unwrap());
}
