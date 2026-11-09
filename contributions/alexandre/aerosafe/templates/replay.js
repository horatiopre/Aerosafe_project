"use strict";
// Clock in milliseconds; positions are observations, never interpolated.
class ReplayClock {
 constructor(points) {
  this.times=points.map(p=>Date.parse(p.position_time));
  if(this.times.some((t,i)=>!Number.isFinite(t)||(i>0&&t<=this.times[i-1])))throw new Error("Dates non ordonnées");
  this.duration=this.times.length>1?this.times.at(-1)-this.times[0]:0;
  this.offset=0;
 }
 seek(value) {this.offset=Math.max(0,Math.min(this.duration,Number.isFinite(value)?value:0));return this.frame();}
 advance(delta,speed) {return this.seek(this.offset+Math.max(0,delta)*speed);}
 frame() {
  if(!this.times.length)return {index:-1,time:null,gap:false,ended:true};
  const time=this.times[0]+this.offset;
  let low=0,high=this.times.length;
  while(low<high){const mid=(low+high)>>>1;if(this.times[mid]<=time)low=mid+1;else high=mid;}
  const index=low-1;
  return {index,time,gap:time-this.times[index]>300000,ended:this.offset>=this.duration};
 }
}
if(typeof module!=="undefined")module.exports={ReplayClock};
