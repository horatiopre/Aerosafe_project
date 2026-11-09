const {test}=require('node:test');
const assert=require('node:assert/strict');
const {ReplayClock}=require('../aerosafe/templates/replay.js');
const points=seconds=>seconds.map(s=>({position_time:new Date(Date.UTC(2026,0,1)+s*1000).toISOString()}));
test('time between samples retains the earlier observation',()=>{
 const clock=new ReplayClock(points([0,10,20]));
 assert.equal(clock.seek(9999).index,0);
 assert.equal(clock.seek(10000).index,1);
});
test('speed scales elapsed time and end is clamped',()=>{
 const clock=new ReplayClock(points([0,10,20]));
 assert.equal(clock.advance(500,10).time,Date.UTC(2026,0,1)+5000);
 assert.equal(clock.advance(10000,60).ended,true);
 assert.equal(clock.offset,20000);
 assert.equal(clock.frame().index,2);
});
test('seeking backwards and restarting restore the correct point',()=>{
 const clock=new ReplayClock(points([0,10,20]));
 clock.seek(20000);assert.equal(clock.seek(15000).index,1);
 assert.equal(clock.seek(-20).index,0);assert.equal(clock.offset,0);
});
test('a gap hides stale positions until the next observation',()=>{
 const clock=new ReplayClock(points([0,700]));
 assert.equal(clock.seek(300000).gap,false);
 assert.equal(clock.seek(300001).gap,true);
 assert.equal(clock.seek(700000).gap,false);
 assert.equal(clock.frame().index,1);
});
test('empty and single point trajectories cannot advance',()=>{
 assert.equal(new ReplayClock([]).frame().index,-1);
 const clock=new ReplayClock(points([0]));
 assert.equal(clock.duration,0);assert.equal(clock.advance(1000,30).ended,true);
});
test('invalid or unordered times are rejected',()=>{
 assert.throws(()=>new ReplayClock(points([10,0])));
 assert.throws(()=>new ReplayClock(points([0,0])));
 assert.throws(()=>new ReplayClock([{position_time:'invalid'}]));
});
